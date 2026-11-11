from django import forms

from inventory.models import GroceryBatch
from inventory.receipt import MAX_RECEIPT_ROWS


class GroceryBatchForm(forms.ModelForm):
    class Meta:
        model = GroceryBatch
        fields = ("name", "quantity", "unit", "storage", "expires_on")
        labels = {"expires_on": "Expiry date"}
        widgets = {"expires_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}


class ReceiptBatchForm(GroceryBatchForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["storage"].choices = [("", "Choose storage"), *GroceryBatch.Storage.choices]
        self.initial.setdefault("storage", "")


class ReceiptReviewFormSet(forms.BaseFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields["DELETE"].label = "Skip this item"


ReceiptBatchFormSet = forms.formset_factory(
    ReceiptBatchForm, formset=ReceiptReviewFormSet, extra=0, can_delete=True, min_num=1, validate_min=True,
    max_num=MAX_RECEIPT_ROWS, validate_max=True, absolute_max=MAX_RECEIPT_ROWS,
)
