"""Optional fixture for demonstrating receiver-confirmed payments."""
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from households.models import Workspace, Membership
from expenses.models import Expense
from expenses.services import request_payment, save_expense


class Command(BaseCommand):
    help = "Add an optional Maple House expense demo to an existing account."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Your existing username. Its password is preserved.")
        parser.add_argument("--display-name", help="Optional name for your new demo membership.")
        parser.add_argument("--demo-password", help="Optional password for the new Alex and Jamie demo accounts.")

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if user is None:
            raise CommandError("Create your account first, then use its username.")
        home, _ = Workspace.objects.get_or_create(name="Maple House · expenses demo")
        people = []
        owner, _ = Membership.objects.get_or_create(workspace=home, user=user, defaults={
            "display_name": options["display_name"] or user.first_name or user.username, "role": Membership.MemberRole.OWNER})
        people.append(owner)
        for name in ("Alex", "Jamie"):
            demo, created = get_user_model().objects.get_or_create(username="hestia-demo-" + name.lower())
            if created:
                if options["demo_password"]:
                    demo.set_password(options["demo_password"])
                else:
                    demo.set_unusable_password()
                demo.save()
            member, _ = Membership.objects.get_or_create(workspace=home, user=demo, defaults={"display_name": name})
            people.append(member)
        if Expense.objects.filter(workspace=home).exists():
            self.stdout.write("Demo already exists. No purchases or payments were added.")
            return
        for title, amount, payer, category, offsets in [
            ("Our weekly groceries", 8430, 0, "groceries", 1),
            ("A little home refresh", 2400, 0, "home", 2),
            ("Internet, sorted", 6000, 1, "bills", 3),
            ("Friday pasta night", 3600, 2, "social", 4),
        ]:
            base, remainder = divmod(amount, 3)
            shares = {member.pk: base + (index < remainder) for index, member in enumerate(people)}
            save_expense(owner, {"title": title, "amount": Decimal(amount)/100, "paid_by": people[payer],
                "date": timezone.localdate() - timezone.timedelta(days=offsets), "category": category,
                "note": "", "split_method": "equal"}, shares, uuid4())
        request_payment(people[1], owner, 300, "Sent after the grocery run", uuid4())
        self.stdout.write(self.style.SUCCESS("Maple House is ready. Open /expenses/ and choose the demo household."))
        self.stdout.write("Alex: hestia-demo-alex · Jamie: hestia-demo-jamie")
        if not options["demo_password"]:
            self.stdout.write("The two new demo accounts have no login password. Set one through Django admin if you need to sign in as them.")
