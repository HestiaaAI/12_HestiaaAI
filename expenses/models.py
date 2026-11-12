"""Household expenses and payments, stored as integer USD cents."""
import uuid
from django.db import models
from households.models import Membership, Workspace


class Expense(models.Model):
    class Category(models.TextChoices):
        GROCERIES = "groceries", "Groceries"
        BILLS = "bills", "Bills"
        HOME = "home", "For the home"
        SOCIAL = "social", "Together"
        OTHER = "other", "Other"

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="expenses")
    paid_by = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="paid_expenses")
    created_by = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="recorded_expenses")
    title = models.CharField(max_length=120)
    amount_cents = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GROCERIES)
    date = models.DateField()
    note = models.CharField(max_length=500, blank=True)
    split_method = models.CharField(max_length=10, choices=[("equal", "Equally"), ("custom", "Exact amounts"), ("percent", "Percentages"), ("shares", "Shares"), ("itemized", "Itemized")])
    split_data = models.JSONField(default=dict, blank=True)
    request_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    version = models.PositiveIntegerField(default=1)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(amount_cents__gt=0), name="expense_positive_amount")]


class ExpenseShare(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="shares")
    member = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="expense_shares")
    amount_cents = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["expense", "member"], name="unique_expense_share")]


class Settlement(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="settlements")
    sender = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="sent_settlements")
    receiver = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="received_settlements")
    amount_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    request_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    note = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_cents__gt=0), name="settlement_positive_amount"),
            models.CheckConstraint(condition=~models.Q(sender=models.F("receiver")), name="settlement_different_members"),
        ]


class ExpenseEvent(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(Membership, on_delete=models.PROTECT)
    kind = models.CharField(max_length=15, choices=[("created", "Created"), ("edited", "Edited"), ("removed", "Removed"), ("restored", "Restored"), ("comment", "Comment")])
    text = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


class PurchaseItem(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name='purchase_requests')
    requested_by = models.ForeignKey(Membership, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(default=1)
    is_checked = models.BooleanField(default=False)
    scope = models.CharField(max_length=10, choices=[('household','Household'),('personal','Personal / opt-in')])
    state = models.CharField(max_length=12, default='open', choices=[('open','To buy'),('purchased','Purchased')])
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at','-pk']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='purchase_quantity_positive')]
    @property
    def total_units(self):
        return self.quantity + sum(self.claims.filter(kind='own').values_list('quantity',flat=True))
    def __str__(self):return self.name


class PurchaseClaim(models.Model):
    item = models.ForeignKey(PurchaseItem,on_delete=models.CASCADE,related_name='claims')
    member = models.ForeignKey(Membership,on_delete=models.PROTECT)
    kind = models.CharField(max_length=6,choices=[('shared','Share product'),('own','Own units')])
    quantity = models.PositiveIntegerField(default=1)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['item','member'],name='one_claim_per_item_member'),models.CheckConstraint(condition=models.Q(quantity__gt=0),name='claim_quantity_positive')]


class ReceiptDraft(models.Model):
    workspace = models.ForeignKey(Workspace,on_delete=models.PROTECT)
    actor = models.ForeignKey(Membership,on_delete=models.PROTECT)
    payload = models.JSONField(default=dict)
    confirmed_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class PurchaseReceipt(models.Model):
    workspace = models.ForeignKey(Workspace,on_delete=models.PROTECT)
    submitted_by = models.ForeignKey(Membership,on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    total_cents = models.PositiveIntegerField()
    draft = models.ForeignKey(ReceiptDraft,on_delete=models.PROTECT,related_name='saved_receipts')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['workspace','fingerprint'],name='unique_household_receipt')]


class ReceiptPurchaseLine(models.Model):
    receipt = models.ForeignKey(PurchaseReceipt,on_delete=models.PROTECT,related_name='lines')
    item = models.ForeignKey(PurchaseItem,on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    expense = models.OneToOneField(Expense,on_delete=models.PROTECT,related_name='purchase_line')


class RecurringBill(models.Model):
    ICONS = [('rent','🏠 Rent'),('electricity','⚡ Electricity'),('water','💧 Water'),('internet','🌐 Internet'),('streaming','📺 Streaming'),('music','🎵 Music'),('phone','📱 Phone'),('insurance','🛡️ Insurance'),('other','🧾 Other')]
    icon = models.CharField(max_length=20, choices=ICONS, default='other')
    notes = models.CharField(max_length=500, blank=True)
    reminder_days = models.PositiveSmallIntegerField(choices=[(0,'On the due date'),(1,'1 day before'),(3,'3 days before'),(7,'1 week before')], default=3)
    reminders_enabled = models.BooleanField(default=True)
    anchor_day = models.PositiveSmallIntegerField(default=0)
    @property
    def emoji(self):
        return dict(self.ICONS).get(self.icon, '🧾 Other').split(' ')[0]
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name='recurring_bills')
    title = models.CharField(max_length=120)
    amount_cents = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=Expense.Category.choices, default='bills')
    paid_by = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='recurring_paid')
    created_by = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='recurring_created')
    participants = models.ManyToManyField(Membership, related_name='recurring_shares')
    next_due = models.DateField()
    frequency = models.CharField(max_length=10, choices=[('monthly','Monthly'),('weekly','Weekly'),('yearly','Yearly')], default='monthly')
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ['next_due','pk']
        constraints = [models.CheckConstraint(condition=models.Q(amount_cents__gt=0), name='recurring_positive_amount')]


class RecurringBillEntry(models.Model):
    bill = models.ForeignKey(RecurringBill, on_delete=models.PROTECT)
    due = models.DateField()
    expense = models.OneToOneField(Expense, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['bill','due'],name='unique_recurring_due')]


class BillReminder(models.Model):
    bill = models.ForeignKey(RecurringBill, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    due = models.DateField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['bill','user','due'],name='unique_bill_reminder')]

class PushSubscription(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=2000, unique=True)
    keys = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class BillPushDelivery(models.Model):
    reminder = models.ForeignKey(BillReminder, on_delete=models.CASCADE)
    subscription = models.ForeignKey(PushSubscription, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['reminder','subscription'],name='unique_bill_push_delivery')]
