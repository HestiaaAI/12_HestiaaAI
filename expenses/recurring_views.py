"""Planned bills become spending only after a roommate records the actual bill."""
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .models import RecurringBill, RecurringBillEntry, Expense
from .views import membership,page_context
from .services import save_expense,lock_household,cents
from .insights import household_today
from .bill_calendar import month_calendar,advance
from .reminders import collect_reminders

class BillForm(forms.Form):
    icon=forms.ChoiceField(choices=RecurringBill.ICONS,required=False,label='Bill type / icon')
    notes=forms.CharField(max_length=500,required=False,widget=forms.Textarea(attrs={'rows':3}),label='Details / notes')
    reminders_enabled=forms.BooleanField(required=False,initial=True,label='Remind everyone sharing this bill')
    reminder_days=forms.TypedChoiceField(choices=RecurringBill._meta.get_field('reminder_days').choices,coerce=int,initial=3,required=False,empty_value=3,label='Reminder timing')
    title=forms.CharField(max_length=120,label='Bill name')
    amount=forms.DecimalField(min_value=Decimal('.01'),max_value=Decimal('999999.99'),decimal_places=2,label='Expected amount · USD')
    category=forms.ChoiceField(choices=Expense.Category.choices,initial='bills')
    next_due=forms.DateField(widget=forms.DateInput(attrs={'type':'date'}),label='Next due date')
    frequency=forms.ChoiceField(choices=RecurringBill._meta.get_field('frequency').choices)
    paid_by=forms.ModelChoiceField(queryset=RecurringBill.objects.none(),label='Who usually pays?')
    participants=forms.ModelMultipleChoiceField(queryset=RecurringBill.objects.none(),widget=forms.CheckboxSelectMultiple,label='Split equally between')
    def __init__(self,*args,actor,**kwargs):
        super().__init__(*args,**kwargs)
        self.order_fields(['icon','title','amount','next_due','frequency','paid_by','participants','category','notes','reminders_enabled','reminder_days'])
        people=actor.workspace.memberships.filter(is_active=True,user__isnull=False)
        for key in ('paid_by','participants'):
            self.fields[key].queryset=people
            self.fields[key].label_from_instance=lambda person: person.display_name

@login_required
@never_cache
def recurring(request,workspace_id):
    actor=membership(request,workspace_id)
    today=household_today(actor.workspace)
    bills=actor.workspace.recurring_bills.select_related('paid_by').prefetch_related('participants')
    selected=None
    selected_id=request.POST.get('bill_id') or request.GET.get('edit') or request.GET.get('bill')
    if selected_id:
        selected=get_object_or_404(bills,pk=selected_id)
    editing=bool(request.POST.get('bill_id') or request.GET.get('edit'))
    can_edit=not selected or actor.pk in (selected.created_by_id,selected.paid_by_id) or actor.role=='OWNER'
    if editing and not can_edit:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    initial={'paid_by':actor.pk,'participants':list(actor.workspace.memberships.filter(is_active=True).values_list('pk',flat=True))}
    if editing and selected:
        initial.update({name:getattr(selected,name) for name in ('title','category','next_due','frequency','icon','notes','reminder_days','reminders_enabled')})
        initial.update(amount=Decimal(selected.amount_cents)/100,paid_by=selected.paid_by_id,participants=list(selected.participants.values_list('pk',flat=True)))
    form=BillForm(request.POST if request.method=='POST' else None,actor=actor,initial=initial)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            lock_household(actor)
            data=form.cleaned_data.copy();people=data.pop('participants');amount=data.pop('amount');data['icon']=data['icon'] or 'other'
            if editing:
                bill=selected
                for key,value in data.items():setattr(bill,key,value)
                bill.amount_cents=cents(amount);bill.anchor_day=data['next_due'].day;bill.save()
            else:
                bill=RecurringBill.objects.create(workspace=actor.workspace,created_by=actor,amount_cents=cents(amount),anchor_day=data['next_due'].day,**data)
            bill.participants.set(people)
        return redirect('expenses:recurring',workspace_id=workspace_id)
    try:
        year=int(request.GET.get('year',today.year));month=int(request.GET.get('month',today.month))
        if not 2000<=year<=2100 or not 1<=month<=12:raise ValueError
    except (ValueError,TypeError):year,month=today.year,today.month
    calendar=month_calendar(list(bills),year,month,today)
    collect_reminders(actor.workspace)
    return render(request,'expenses/recurring.html',{**page_context(actor),'form':form,'bills':bills,'today':today,'calendar':calendar,'selected':selected,'editing':editing,'can_edit':can_edit})

@login_required
@require_POST
@transaction.atomic
def recurring_action(request,workspace_id,bill_id):
    actor=membership(request,workspace_id);lock_household(actor)
    bill=get_object_or_404(RecurringBill,pk=bill_id,workspace=actor.workspace)
    error=''
    action=request.POST.get('action')
    if action in ('pause','resume'):
        if actor.pk not in (bill.created_by_id,bill.paid_by_id) and actor.role!='OWNER':
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        bill.active=action=='resume';bill.save(update_fields=['active'])
    elif action=='record':
        try:
            if not bill.active:raise ValidationError('Resume this bill before recording it.')
            due=forms.DateField().clean(request.POST.get('due'))
            if RecurringBillEntry.objects.filter(bill=bill,due=due).exists():
                return redirect('expenses:recurring',workspace_id=workspace_id)
            if due!=bill.next_due:raise ValidationError('This bill changed. Reload the page before recording it.')
            amount=forms.DecimalField(min_value=Decimal('.01'),max_value=Decimal('999999.99'),decimal_places=2).clean(request.POST.get('amount'))
            people=list(bill.participants.filter(is_active=True,workspace=actor.workspace))
            if not people or not bill.paid_by.is_active:raise ValidationError('The payer and at least one participant must still be active household members.')
            total=cents(amount);base,remainder=divmod(total,len(people))
            expense=save_expense(actor,{'title':bill.title,'amount':amount,'paid_by':bill.paid_by,'category':bill.category,'date':due,'split_method':'equal','note':'Recurring bill · '+due.isoformat()}, {p.pk:base+(i<remainder) for i,p in enumerate(people)},uuid4())
            RecurringBillEntry.objects.create(bill=bill,due=due,expense=expense)
            bill.next_due=advance(due,bill.frequency,bill.anchor_day)
            bill.save(update_fields=['next_due'])
        except ValidationError as exc:error=' '.join(exc.messages)
    else:error='Choose a valid bill action.'
    if error:
        from django.contrib import messages
        messages.error(request,error)
    return redirect('expenses:recurring',workspace_id=workspace_id)
