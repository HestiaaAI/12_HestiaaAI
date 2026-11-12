from calendar import Calendar,monthrange,month_name
from datetime import date,timedelta
from .models import RecurringBillEntry

def advance(due,frequency,anchor):
    if frequency=='weekly':return due+timedelta(days=7)
    month=due.month+(1 if frequency=='monthly' else 12)
    year=due.year+(month-1)//12;month=(month-1)%12+1
    return date(year,month,min(anchor or due.day,monthrange(year,month)[1]))

def month_calendar(bills,year,month,today):
    start=date(year,month,1);end=date(year,month,monthrange(year,month)[1]);events={}
    for bill in bills:
        if not bill.active:continue
        due=bill.next_due
        # Jump close to the selected period before bounded projection.
        if bill.frequency=='weekly' and due<start:
            due+=timedelta(days=max(0,(start-due).days//7)*7)
        elif bill.frequency=='monthly' and due<start:
            due=date(year,month,min(bill.anchor_day or due.day,monthrange(year,month)[1]))
        elif bill.frequency=='yearly' and due.year<year:
            due=date(year,due.month,min(bill.anchor_day or due.day,monthrange(year,due.month)[1]))
        for _ in range(33):
            if due>end:break
            if due>=start:
                events.setdefault(due,[]).append({'bill':bill,'amount':bill.amount_cents,'status':'Overdue' if due<today else 'Due today' if due==today else 'Upcoming','due':due})
            due=advance(due,bill.frequency,bill.anchor_day)
    for entry in RecurringBillEntry.objects.filter(bill__in=bills,due__range=(start,end)).select_related('bill','expense'):
        events.setdefault(entry.due,[]).append({'bill':entry.bill,'amount':entry.expense.amount_cents,'status':'Recorded','due':entry.due})
    weeks=[[{'date':day,'outside':day.month!=month,'today':day==today,'events':events.get(day,[])} for day in week] for week in Calendar(firstweekday=0).monthdatescalendar(year,month)]
    prev=start-timedelta(days=1);following=end+timedelta(days=1)
    return {'weeks':weeks,'month_name':month_name[month],'year':year,'month':month,'previous':prev,'following':following,'scheduled_total':sum(e['amount'] for values in events.values() for e in values if e['status']!='Recorded'),'event_count':sum(map(len,events.values()))}
