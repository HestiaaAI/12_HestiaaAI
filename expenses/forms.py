"""Household-scoped expense and payment forms."""
import uuid
from decimal import Decimal
from django import forms
from django.db.models import Q
from django.utils import timezone

from households.models import Membership
from .models import Expense
from .services import cents

MONEY = {"max_digits": 8, "decimal_places": 2, "min_value": Decimal("0.01"), "max_value": Decimal("999999.99")}


class RoommateChoice(forms.ModelChoiceField):
    def label_from_instance(self, member):
        return member.display_name


class RoommatesChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, member):
        return member.display_name


class ExpenseForm(forms.Form):
    title = forms.CharField(max_length=120, label="What was it for?", widget=forms.TextInput(attrs={"placeholder": "e.g. Our weekly groceries"}))
    amount = forms.DecimalField(label="Total paid (USD)", **MONEY)
    paid_by = RoommateChoice(queryset=Membership.objects.none(), label="Who paid?")
    date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}))
    category = forms.ChoiceField(choices=Expense.Category.choices)
    split_method = forms.ChoiceField(choices=[("equal", "Equal"), ("custom", "Exact"), ("percent", "%"), ("shares", "Shares"), ("itemized", "Itemized")], widget=forms.RadioSelect, initial="equal", label="How should we split it?")
    participants = RoommatesChoice(queryset=Membership.objects.none(), widget=forms.CheckboxSelectMultiple, label="Who is sharing this?")
    note = forms.CharField(max_length=500, required=False, label="A little note (optional)", widget=forms.Textarea(attrs={"rows": 2}))
    request_token = forms.UUIDField(widget=forms.HiddenInput)
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    item_lines = forms.CharField(required=False, max_length=10000, label="Line items: description | amount | roommate ID", widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Milk | 6.00 | 1"}))

    def __init__(self, *args, workspace, actor, expense=None, **kwargs):
        super().__init__(*args, **kwargs)
        history_ids = []
        if expense:
            history_ids = list(expense.shares.values_list("member_id", flat=True)) + [expense.paid_by_id]
        self.members = list(Membership.objects.filter(workspace=workspace).filter(Q(is_active=True, user__is_active=True) | Q(pk__in=history_ids)).order_by("membership_id"))
        ids = [member.pk for member in self.members]
        available = Membership.objects.filter(pk__in=ids).order_by("membership_id")
        self.fields["paid_by"].queryset = available
        self.fields["participants"].queryset = available
        self.initial.update(paid_by=actor.pk, participants=ids, request_token=uuid.uuid4())
        for member in self.members:
            self.fields[f"share_{member.pk}"] = forms.DecimalField(
                required=False, label=member.display_name + " (USD)", max_digits=8,
                decimal_places=2, min_value=Decimal("0"), max_value=Decimal("999999.99"))
        if expense:
            self.initial.update(item_lines=expense.split_data.get("item_lines", ""))
            self.initial.update(title=expense.title, amount=Decimal(expense.amount_cents)/100,
                                paid_by=expense.paid_by_id, date=expense.date, category=expense.category,
                                split_method=expense.split_method, note=expense.note, participants=history_ids[:-1],
                                request_token=expense.request_token, version=expense.version)
            for share in expense.shares.all():
                self.initial[f"share_{share.member_id}"] = (expense.split_data.get("inputs", {}).get(str(share.member_id), Decimal(share.amount_cents)/100))

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("Use the date the purchase was made.")
        return date

    def clean(self):
        values = super().clean()
        if any(key not in values for key in ("amount", "participants", "split_method")):
            return values
        members = sorted(member.pk for member in values["participants"])
        total = cents(values["amount"])
        if values["split_method"] == "equal":
            share, extra = divmod(total, len(members))
            self.shares = {member: share + (index < extra) for index, member in enumerate(members)}
        elif values["split_method"] in ("percent", "shares"):
            inputs = {member: values.get(f"share_{member}") for member in members}
            if any(value is None for value in inputs.values()):
                raise forms.ValidationError("Enter a percentage or share weight for every selected roommate.")
            weight = sum(inputs.values())
            if weight <= 0 or (values["split_method"] == "percent" and weight != 100):
                raise forms.ValidationError("Percentages must total 100; share weights must have a positive total.")
            self.shares = weighted_shares(total, inputs)
            values["split_data"] = {"inputs": {str(k): str(v) for k, v in inputs.items()}}
        elif values["split_method"] == "itemized":
            self.shares = {member: 0 for member in members}
            lines = values.get("item_lines", "").strip()
            if not lines:
                raise forms.ValidationError("Enter at least one line item.")
            for line in lines.splitlines():
                try:
                    title, raw_amount, raw_member = [part.strip() for part in line.split("|")]
                    member = int(raw_member)
                    amount = cents(raw_amount)
                    if not title or member not in self.shares:
                        raise ValueError
                except (ValueError, forms.ValidationError):
                    raise forms.ValidationError("Use description | positive amount | selected roommate ID for each item.")
                self.shares[member] += amount
            if sum(self.shares.values()) != total:
                raise forms.ValidationError("Line items, including tax and tips, must total the amount paid.")
            values["split_data"] = {"item_lines": lines}
        else:
            self.shares = {}
            for member in members:
                value = values.get(f"share_{member}")
                if value is None:
                    self.add_error(f"share_{member}", "Enter this roommate's share.")
                else:
                    self.shares[member] = int(value * 100)
            if len(self.shares) == len(members) and sum(self.shares.values()) != total:
                raise forms.ValidationError("The roommate amounts must add up to the total paid.")
        return values

    @property
    def share_fields(self):
        return [self[f"share_{member.pk}"] for member in self.members]


class PaymentForm(forms.Form):
    receiver = RoommateChoice(queryset=Membership.objects.none(), label="Who did you pay?")
    amount = forms.DecimalField(label="Amount paid (USD)", **MONEY)
    note = forms.CharField(max_length=250, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. Paid through Venmo"}))
    request_token = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["receiver"].queryset = Membership.objects.filter(workspace=actor.workspace, is_active=True, user__isnull=False).exclude(pk=actor.pk)
        self.initial["request_token"] = uuid.uuid4()


def weighted_shares(total, weights):
    denominator = sum(weights.values())
    exact = {member: Decimal(total) * weight / denominator for member, weight in weights.items()}
    result = {member: int(value) for member, value in exact.items()}
    ranked = sorted(exact, key=lambda member: (-(exact[member] - result[member]), member))
    for member in ranked[:total - sum(result.values())]:
        result[member] += 1
    return result
