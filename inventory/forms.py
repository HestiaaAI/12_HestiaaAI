from django import forms

from inventory.models import GroceryBatch


class GroceryBatchForm(forms.ModelForm):
    class Meta:
        model = GroceryBatch
        fields = ("name", "quantity", "unit", "storage", "expires_on")
        labels = {"expires_on": "Expiry date"}
        widgets = {"expires_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}
