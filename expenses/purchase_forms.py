from decimal import Decimal
from django import forms
from django.utils import timezone
from households.models import Membership
from .models import PurchaseItem
from .forms import MONEY, RoommateChoice


class PurchaseItemForm(forms.Form):
    name=forms.CharField(max_length=120,label='What do you want to buy?')
    quantity=forms.IntegerField(min_value=1,max_value=1000,initial=1,label='Units for the original product / shared pool')
    scope=forms.ChoiceField(choices=[('household','Everyone in the household'),('personal','Just me, with opt-in joining')],label='Who starts in the split?')


class JoinPurchaseForm(forms.Form):
    kind=forms.ChoiceField(choices=[('shared','Share the same product’s cost'),('own','Get my own units')])
    quantity=forms.IntegerField(min_value=1,max_value=1000,initial=1,label='Own units (ignored when sharing the same product)')


class ReceiptInputForm(forms.Form):
    payer=RoommateChoice(queryset=Membership.objects.none(),label='Who paid this receipt?')
    date=forms.DateField(initial=timezone.localdate,widget=forms.DateInput(attrs={'type':'date'}))
    total=forms.DecimalField(label='Final receipt total · USD',**MONEY)
    tax=forms.DecimalField(min_value=Decimal('0'),max_digits=8,decimal_places=2,initial=0,label='Tax added after item subtotal · USD')
    discount=forms.DecimalField(min_value=Decimal('0'),max_digits=8,decimal_places=2,initial=0,label='Discount not already included in item prices · USD')
    text=forms.CharField(max_length=16000,label='Receipt text · check OCR before continuing',widget=forms.Textarea(attrs={'rows':7}))
    def __init__(self,*args,workspace,actor,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['payer'].queryset=Membership.objects.filter(workspace=workspace,is_active=True)

ReceiptInputFormSet=forms.formset_factory(ReceiptInputForm,extra=0,min_num=1,validate_min=True,max_num=5,validate_max=True,absolute_max=5)


class ReceiptLineForm(forms.Form):
    line_id=forms.IntegerField(widget=forms.HiddenInput)
    item=forms.ModelChoiceField(queryset=PurchaseItem.objects.none(),label='Match to requested item (or choose baskets below)',required=False)
    recipients=forms.ModelMultipleChoiceField(queryset=Membership.objects.none(),required=False,widget=forms.CheckboxSelectMultiple,label='Who gets this item? Choose one or more baskets')
    quantity=forms.IntegerField(min_value=1,max_value=1000,label='Units purchased on this line')
    amount=forms.DecimalField(label='Line total before receipt-level tax/discount · USD',**MONEY)
    def __init__(self,*args,draft,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['item'].queryset=PurchaseItem.objects.filter(workspace=draft.workspace,state='open',pk__in=draft.payload['versions'])
        self.fields['recipients'].queryset=Membership.objects.filter(workspace=draft.workspace,is_active=True,user__isnull=False)
        self.fields['recipients'].label_from_instance=lambda member: member.display_name
        metadata={r['line_id']:{**r,'receipt_number':i+1} for i,receipt in enumerate(draft.payload['receipts']) for r in receipt['rows']}
        try:key=int(self.data.get(self.add_prefix('line_id'))) if self.is_bound else self.initial.get('line_id')
        except (TypeError,ValueError):key=None
        self.metadata=metadata.get(key,{})

    def clean(self):
        values=super().clean()
        if values.get('item') and values.get('recipients'):
            raise forms.ValidationError('Choose an existing list item or roommate baskets, not both.')
        if not values.get('item') and not values.get('recipients'):
            raise forms.ValidationError('Place this item in at least one roommate basket or match it to the list.')
        return values

ReceiptLineFormSet=forms.formset_factory(ReceiptLineForm,extra=0,min_num=1,validate_min=True,max_num=200,validate_max=True,absolute_max=200)
