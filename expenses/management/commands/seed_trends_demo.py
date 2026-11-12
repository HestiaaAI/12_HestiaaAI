"""Create an isolated, repeatable household with clearly labelled sample history."""
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from households.models import Workspace, Membership
from expenses.models import Expense, ExpenseEvent, Settlement
from expenses.services import save_expense, request_payment, resolve_payment

class Command(BaseCommand):
    help = 'Create A/B/C demo expense history for an existing account; never replaces existing data.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['username']).first()
        if user is None:
            raise CommandError('Existing account not found.')
        name = f'The Test Home · A, B & C · {user.username}'
        home, _ = Workspace.objects.get_or_create(name=name)
        a, _ = Membership.objects.get_or_create(workspace=home, user=user, defaults={'display_name':'A', 'role':'OWNER'})
        members = [a]
        for label in ('B','C'):
            demo, created = get_user_model().objects.get_or_create(username=f'trends-demo-{user.pk}-{label.lower()}')
            if created:
                demo.set_unusable_password()
                demo.save()
            member, _ = Membership.objects.get_or_create(workspace=home, user=demo, defaults={'display_name':label})
            members.append(member)
        if home.expenses.exists():
            self.stdout.write(f'Demo already exists; no records added. /expenses/{home.pk}/trends/')
            return
        zone = ZoneInfo(home.timezone)
        today = timezone.localtime(timezone.now(), zone).date()
        count = 0
        for month in range(1, today.month+1):
            # November (or the live current month) intentionally differs from the previous month.
            records = [
                ('Rent', 180000, 0, 'bills', [0,1,2], 1),
                ('Weekly groceries', 10500 + (month%4)*2400, month%3, 'groceries', [0,1,2], 3),
                ('Electricity and internet', 13500 + month*300, 1, 'bills', [0,1,2], 5),
                ('Dinner together', 6600 + (month%3)*1800, 2, 'social', [0,1,2], 7),
                ('A’s personal essentials', 1800 + (month%5)*1200, 0, 'other', [0], 8),
                ('A + B coffee run', 1800 + month*100, 1, 'social', [0,1], 9),
                ('Kitchen supplies', 2400 + (month%4)*1500, 0, 'home', [0,1,2], 10),
            ]
            for title, amount, payer, category, people, day in records:
                when = date(today.year,month,min(day,monthrange(today.year,month)[1]))
                if when > today:
                    continue
                if month == today.month and category == 'groceries':
                    amount += 7200
                base, remainder = divmod(amount,len(people))
                shares = {members[idx].pk:base+(i<remainder) for i,idx in enumerate(people)}
                exp = save_expense(members[payer], {'title':title, 'amount':Decimal(amount)/100, 'paid_by':members[payer], 'date':when, 'category':category, 'note':'SAMPLE DATA · demo only, not a real purchase.', 'split_method':'equal'}, shares, uuid4())
                stamp = datetime.combine(when,time(12),tzinfo=zone)
                Expense.objects.filter(pk=exp.pk).update(created_at=stamp,updated_at=stamp)
                ExpenseEvent.objects.filter(expense=exp).update(created_at=stamp)
                count += 1
            if month < today.month:
                payment = request_payment(members[1], a, 10000, 'SAMPLE · monthly partial settlement', uuid4())
                resolve_payment(a, payment.pk, 'confirm')
                stamp = datetime(today.year,month, min(12,monthrange(today.year,month)[1]),12,tzinfo=zone)
                Settlement.objects.filter(pk=payment.pk).update(created_at=stamp,resolved_at=stamp+timedelta(hours=2))
        pending = request_payment(members[2], a, 2500, 'SAMPLE · awaiting A’s confirmation', uuid4())
        ExpenseEvent.objects.create(expense=exp, actor=members[1], kind='comment', text='SAMPLE · thanks for picking these up!')
        assert home.memberships.count() == 3
        for expense in home.expenses.all():
            assert sum(expense.shares.values_list('amount_cents',flat=True)) == expense.amount_cents
        self.stdout.write(self.style.SUCCESS(f'Created {count} sample expenses, {home.settlements.count()} payment records and 3 roommates.'))
        self.stdout.write(f'Overview: /expenses/{home.pk}/\nTrends: /expenses/{home.pk}/trends/\nActivity: /expenses/{home.pk}/activity/')
        self.stdout.write('Your account is A. B and C are demo accounts with no login passwords. No real money was moved.')
