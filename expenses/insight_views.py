from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.utils import timezone
from households.models import Membership
from .models import Expense
from .views import membership,page_context
from .insights import household_today,household_zone,spending_report,activity_rows


class TrendFilter(forms.Form):
    year=forms.IntegerField(min_value=2000,max_value=2100)
    month=forms.IntegerField(min_value=1,max_value=12)


class ActivityFilter(forms.Form):
    person=forms.ModelChoiceField(queryset=Membership.objects.none(),required=False,label='Roommate')
    kind=forms.ChoiceField(required=False,choices=[('','All activity'),('created','Expenses added'),('edited','Expenses edited'),('comment','Comments'),('removed','Expenses removed'),('restored','Expenses restored'),('payment_recorded','Payments recorded'),('payment_confirmed','Payments confirmed'),('payment_rejected','Payments declined'),('payment_cancelled','Payments cancelled')])
    since=forms.DateField(required=False,widget=forms.DateInput(attrs={'type':'date'}))
    until=forms.DateField(required=False,widget=forms.DateInput(attrs={'type':'date'}))
    def __init__(self,*args,workspace,actor=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['person'].queryset=Membership.objects.filter(workspace=workspace).order_by('display_name','pk')
        self.fields['person'].label_from_instance=lambda member: (member.display_name or 'Roommate')+(' (you)' if actor and member.pk==actor.pk else '')
    def clean(self):
        values=super().clean()
        if values.get('since') and values.get('until') and values['since']>values['until']:raise forms.ValidationError('Start date must be on or before the end date.')
        return values


@login_required
@never_cache
def trends(request,workspace_id):
    actor=membership(request,workspace_id);today=household_today(actor.workspace)
    filters=TrendFilter({'year':request.GET.get('year',today.year),'month':request.GET.get('month',today.month)})
    valid=filters.is_valid();year=filters.cleaned_data['year'] if valid else today.year;month=filters.cleaned_data['month'] if valid else today.month
    earliest=Expense.objects.filter(workspace=actor.workspace,voided_at=None).order_by('date').values_list('date',flat=True).first()
    years=range(max(2000,min(earliest.year if earliest else today.year,today.year-1)),min(2100,today.year+1)+1)
    import calendar
    report=spending_report(actor,year,month,today)
    return render(request,'expenses/trends.html',{**page_context(actor),'report':report,'filters':filters,'years':years,'month_choices':[(m,calendar.month_name[m]) for m in range(1,13)]})


@login_required
@never_cache
def activity(request,workspace_id):
    actor=membership(request,workspace_id)
    return render(request,'expenses/activity.html',{**page_context(actor),**activity_context(request,actor)})


def activity_context(request,actor):
    form=ActivityFilter(request.GET,workspace=actor.workspace,actor=actor);rows=[]
    if form.is_valid():
        values=form.cleaned_data;zone=household_zone(actor.workspace)
        for row in activity_rows(actor.workspace):
            if values.get('person') and row['actor_id']!=values['person'].pk:continue
            if values.get('kind') and row['kind']!=values['kind']:continue
            day=timezone.localtime(row['at'],zone).date()
            if values.get('since') and day<values['since']:continue
            if values.get('until') and day>values['until']:continue
            rows.append(row)
    page=Paginator(rows,25).get_page(request.GET.get('page'))
    query=request.GET.copy();query.pop('page',None)
    return {'filter_form':form,'page':page,'query':query.urlencode(),'activity_timezone':household_zone(actor.workspace)}
