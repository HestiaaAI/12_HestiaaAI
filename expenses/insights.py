"""Recorded spending uses expense shares; settlements never become spending."""
import calendar
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal,ROUND_HALF_UP
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from django.db.models import Count,Q,Sum
from django.utils import timezone
from .models import Expense,ExpenseShare,ExpenseEvent,Settlement


def household_zone(workspace):
    try:return ZoneInfo(workspace.timezone)
    except (ZoneInfoNotFoundError,ValueError):return timezone.get_current_timezone()


def household_today(workspace):return timezone.localdate(timezone=household_zone(workspace))


def spending_report(actor,year,month,today=None):
    today=today or household_today(actor.workspace)
    start=date(year,month,1);end=date(year+int(month==12),month%12+1,1)
    prior_end=start;prior_start=(start-timedelta(days=1)).replace(day=1)
    in_progress=year==today.year and month==today.month
    comparison_end=prior_end
    if in_progress:comparison_end=prior_start+timedelta(days=min(today.day,calendar.monthrange(prior_start.year,prior_start.month)[1]))
    first=min(date(year,1,1),prior_start)
    shares=list(ExpenseShare.objects.filter(member=actor,expense__workspace=actor.workspace,expense__voided_at=None,amount_cents__gt=0,expense__date__gte=first,expense__date__lte=today)
        .select_related('expense').annotate(beneficiaries=Count('expense__shares',filter=Q(expense__shares__amount_cents__gt=0),distinct=True)))
    selected=[s for s in shares if start<=s.expense.date<end]
    previous=[s for s in shares if prior_start<=s.expense.date<prior_end]
    comparison=[s for s in previous if s.expense.date<comparison_end]
    current_total=sum(s.amount_cents for s in selected);previous_total=sum(s.amount_cents for s in previous);baseline=sum(s.amount_cents for s in comparison)
    personal=sum(s.amount_cents for s in selected if s.beneficiaries==1);shared=current_total-personal
    month_data=[{'number':i,'name':calendar.month_abbr[i],'total':0,'personal':0,'shared':0,'future':date(year,i,1)>today} for i in range(1,13)]
    for s in shares:
        if s.expense.date.year==year:
            row=month_data[s.expense.date.month-1];row['total']+=s.amount_cents;row['personal' if s.beneficiaries==1 else 'shared']+=s.amount_cents
    largest=max((m['total'] for m in month_data),default=0) or 1
    for row in month_data:
        row.update(height=max(2,round(row['total']/largest*100)),personal_height=round(row['personal']/largest*100,2),shared_height=round(row['shared']/largest*100,2),selected=row['number']==month)
    categories=[]
    for key,label in Expense.Category.choices:
        value=sum(s.amount_cents for s in selected if s.expense.category==key);previous_value=sum(s.amount_cents for s in comparison if s.expense.category==key)
        categories.append({'key':key,'label':label,'total':value,'previous':previous_value,'delta':value-previous_value,'delta_abs':abs(value-previous_value),'percent':round(value/current_total*100) if current_total else 0})
    categories.sort(key=lambda c:c['total'],reverse=True)
    year_total=sum(m['total'] for m in month_data);observed_months=12 if year<today.year else today.month if year==today.year else 0
    household=Expense.objects.filter(workspace=actor.workspace,voided_at=None,date__gte=start,date__lt=end,date__lte=today)
    pending=Settlement.objects.filter(workspace=actor.workspace,status='pending').filter(Q(sender=actor)|Q(receiver=actor))
    peak=max(month_data,key=lambda m:m['total']) if year_total else None
    days=defaultdict(int)
    for s in selected:days[s.expense.date]+=s.amount_cents
    busiest=max(days,key=days.get) if days else None
    return {'year':year,'month':month,'month_name':calendar.month_name[month],'previous_name':calendar.month_name[prior_start.month],
        'comparison_label':f'first {min(today.day,calendar.monthrange(prior_start.year,prior_start.month)[1])} days of {calendar.month_name[prior_start.month]}' if in_progress else calendar.month_name[prior_start.month],
        'in_progress':in_progress,'future_period':start>today,'your_spend':current_total,'previous_full':previous_total,'comparison_spend':baseline,
        'delta':current_total-baseline,'delta_abs':abs(current_total-baseline),'change_percent':round((current_total-baseline)/baseline*100,1) if baseline else None,
        'change_percent_abs':round(abs(current_total-baseline)/baseline*100,1) if baseline else None,
        'household_spend':household.aggregate(total=Sum('amount_cents'))['total'] or 0,
        'your_upfront':household.filter(paid_by=actor).aggregate(total=Sum('amount_cents'))['total'] or 0,
        'personal_spend':personal,'shared_spend':shared,'personal_percent':round(personal/current_total*100) if current_total else 0,
        'months':month_data,'year_total':year_total,'monthly_average':int((Decimal(year_total)/observed_months).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if observed_months else 0,
        'peak':peak,'categories':categories,'top_category':categories[0] if current_total else None,
        'purchase_count':len(selected),'average_purchase':int((Decimal(current_total)/len(selected)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if selected else 0,
        'largest_purchases':sorted(selected,key=lambda s:s.amount_cents,reverse=True)[:5],
        'pending_amount':pending.aggregate(total=Sum('amount_cents'))['total'] or 0,'pending_count':pending.count(),
        'busiest_date':busiest,'busiest_total':days[busiest] if busiest else 0}


def activity_rows(workspace):
    rows=[]
    for event in ExpenseEvent.objects.filter(expense__workspace=workspace).select_related('actor__user','expense'):
        rows.append({'id':f'event-{event.pk}','at':event.created_at,'kind':event.kind,'actor_id':event.actor_id,'actor':event.actor,'expense':event.expense,
            'verb':{'created':'added an expense','edited':'edited an expense','removed':'removed an expense','restored':'restored an expense','comment':'commented on an expense'}[event.kind],
            'title':event.expense.title,'text':event.text,'amount':event.expense.amount_cents,'current_value':True})
    for expense in Expense.objects.filter(workspace=workspace).exclude(events__kind='created').select_related('created_by__user'):
        rows.append({'id':f'legacy-{expense.pk}','at':expense.created_at,'kind':'created','actor_id':expense.created_by_id,'actor':expense.created_by,'expense':expense,'verb':'added an expense','title':expense.title,'text':'','amount':expense.amount_cents,'current_value':True})
    for payment in Settlement.objects.filter(workspace=workspace).select_related('sender__user','receiver__user'):
        rows.append({'id':f'payment-{payment.pk}-created','at':payment.created_at,'kind':'payment_recorded','actor_id':payment.sender_id,'actor':payment.sender,
            'verb':'recorded a payment','title':f'{payment.sender.display_name} → {payment.receiver.display_name}','text':f'Current status: {payment.get_status_display()}','amount':payment.amount_cents,'current_value':False})
        if payment.resolved_at and payment.status!='pending':
            member=payment.sender if payment.status=='cancelled' else payment.receiver
            rows.append({'id':f'payment-{payment.pk}-resolved','at':payment.resolved_at,'kind':f'payment_{payment.status}','actor_id':member.pk,'actor':member,
                'verb':{'confirmed':'confirmed receiving a payment','rejected':'declined a payment','cancelled':'cancelled a payment record'}[payment.status],
                'title':f'{payment.sender.display_name} → {payment.receiver.display_name}','text':payment.note,'amount':payment.amount_cents,'current_value':False})
    return sorted(rows,key=lambda r:(r['at'],r['id']),reverse=True)
