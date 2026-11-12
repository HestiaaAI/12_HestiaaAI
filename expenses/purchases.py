"""Opt-in purchase claims and atomic, reviewed receipt-to-ledger reconciliation."""
import hashlib
import re
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from households.models import Membership
from inventory.receipt import PRICE, SUMMARY, COUNT_PREFIX, QUANTITY_LINE
from .models import PurchaseItem, PurchaseClaim, ReceiptDraft, PurchaseReceipt, ReceiptPurchaseLine
from .services import lock_household, save_expense, cents
from .forms import weighted_shares
from .purchase_matching import suggest_matches


def nonnegative_cents(value):
    try:
        value=Decimal(str(value))
        if not value.is_finite() or value<0 or value>Decimal('999999.99') or value*100!=(value*100).to_integral_value():raise ValueError
        return int(value*100)
    except (InvalidOperation,ValueError,TypeError):raise ValidationError('Use a nonnegative amount with at most two decimal places.')


@transaction.atomic
def create_item(actor,name,quantity,scope):
    actor=lock_household(actor)
    name=str(name).strip()
    if not name or len(name)>120 or type(quantity) is not int or not 1<=quantity<=1000 or scope not in ('household','personal'):
        raise ValidationError('Add a name, 1–1000 units and a valid list type.')
    item=PurchaseItem.objects.create(workspace=actor.workspace,requested_by=actor,name=name,quantity=quantity,scope=scope)
    people=Membership.objects.filter(workspace=actor.workspace,is_active=True, user__is_active=True) if scope=='household' else [actor]
    PurchaseClaim.objects.bulk_create([PurchaseClaim(item=item,member=p,kind='shared',quantity=1) for p in people])
    return item


@transaction.atomic
def join_item(actor,item_id,kind,quantity=1):
    actor=lock_household(actor)
    item=PurchaseItem.objects.filter(pk=item_id,workspace=actor.workspace,state='open').first()
    if not item or kind not in ('shared','own') or type(quantity) is not int or not 1<=quantity<=1000:
        raise ValidationError('Choose an open item in your household and a valid join option.')
    if item.claims.filter(member=actor).exists():raise ValidationError('You are already included in this item.')
    PurchaseClaim.objects.create(item=item,member=actor,kind=kind,quantity=quantity if kind=='own' else 1)
    item.version+=1;item.save(update_fields=['version'])
    return item


def claim_weights(item):
    claims=list(item.claims.all());shared=[c for c in claims if c.kind=='shared']
    if not shared:raise ValidationError('An item needs at least one person sharing its original units.')
    return {c.member_id:(item.quantity if c.kind=='shared' else c.quantity*len(shared)) for c in claims}


def receipt_text_lines(text):
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    numbered=[re.match(r'^(\d{1,3})[.)]?\s+(.+)$',line) for line in lines]
    numbers=[int(match.group(1)) for match in numbered if match]
    consecutive=len(numbers)>=3 and len(numbers)>=len(lines)*.7 and all(b==a+1 for a,b in zip(numbers,numbers[1:]))
    quantity_prefix=any(match and re.match(r'^(?:x|×|lb|kg|oz)\b',match.group(2),re.I) for match in numbered)
    for line,match in zip(lines,numbered):
        if consecutive and not quantity_prefix and match:
            line=match.group(2)
        line=re.sub(r'^\d{1,4}[.)]?\s+(?=(?:sub[ -]*total|grand[ -]*total|total|tax|sales[ -]*tax|discount|coupon|savings|cash|change|payment|amount|balance)\b)','',line,flags=re.I)
        yield line


def receipt_rows(text):
    rows=[]
    for line in receipt_text_lines(text):
        line=' '.join(line.split());price=PRICE.search(line)
        if not price or SUMMARY.match(line) or QUANTITY_LINE.match(line):continue
        raw=line[:price.start()].strip(' -:.*')
        count=COUNT_PREFIX.match(raw);quantity=int(count.group(1)) if count else 1
        if count:raw=raw[count.end():]
        raw=re.sub(r'^\d{4,15}\s+','',raw)
        price_number=re.search(r'\d+[.,]\d{2}',price.group()).group().replace(',','.')
        value=nonnegative_cents(price_number)
        if raw and any(c.isalpha() for c in raw) and value>0:
            if quantity>1000 or len(rows)>=40:raise ValidationError('Use at most 40 receipt items, with no more than 1000 units per line.')
            rows.append({'name':raw[:120],'quantity':quantity,'amount_cents':value})
    return rows


def prepare_receipts(actor,receipts,use_ai=False):
    if not Membership.objects.filter(pk=actor.pk,user=actor.user,workspace=actor.workspace,is_active=True, user__is_active=True).exists():raise ValidationError('An active household membership is required.')
    if not 1<=len(receipts)<=5:raise ValidationError('Review between one and five receipts at a time.')
    items=list(PurchaseItem.objects.filter(workspace=actor.workspace,state='open').prefetch_related('claims'))
    if len(items)>300:raise ValidationError('The open list is too long. Finish a trip before scanning more receipts.')
    data=[];fingerprints=set();line_id=0
    for source in receipts:
        text=source['text'].strip()
        if not text or len(text)>16000:raise ValidationError('Receipt text must contain 1–16000 characters.')
        fingerprint=hashlib.sha256(' '.join(text.casefold().split()).encode()).hexdigest()
        if fingerprint in fingerprints or PurchaseReceipt.objects.filter(workspace=actor.workspace,fingerprint=fingerprint).exists():raise ValidationError('This receipt is duplicated or has already been confirmed for this household.')
        fingerprints.add(fingerprint)
        payer=source['payer']
        if not Membership.objects.filter(pk=payer.pk,workspace=actor.workspace,is_active=True, user__is_active=True).exists():raise ValidationError('Choose a payer in this household.')
        try:date=timezone.datetime.strptime(str(source['date']),'%Y-%m-%d').date()
        except ValueError:raise ValidationError('Choose a valid receipt date.')
        if date>timezone.localdate():raise ValidationError('Receipt dates cannot be in the future.')
        rows=receipt_rows(text)
        if not rows:raise ValidationError('No priced items were found. Correct the receipt text, then try again.')
        for row in rows:row['line_id']=line_id;line_id+=1
        data.append({'fingerprint':fingerprint,'payer_id':payer.pk,'date':str(date),'total_cents':cents(source['total']),
                     'tax_cents':nonnegative_cents(source['tax']),'discount_cents':nonnegative_cents(source['discount']),'rows':rows})
    flat=[r for receipt in data for r in receipt['rows']]
    if not Membership.objects.filter(pk=actor.pk,user_id=actor.user_id,workspace=actor.workspace,is_active=True,user__is_active=True).exists():
        raise ValidationError('An active household membership is required.')
    matches,status=suggest_matches([r['name'] for r in flat],items,use_ai)
    for row,match in zip(flat,matches):row.update(match)
    with transaction.atomic():
        actor=lock_household(actor)
        return ReceiptDraft.objects.create(workspace=actor.workspace,actor=actor,payload={'receipts':data,'versions':{str(i.pk):i.version for i in items},'matching_status':status})


@transaction.atomic
def confirm_receipts(actor,draft_id,rows,confirmed):
    actor=lock_household(actor)
    draft=ReceiptDraft.objects.filter(pk=draft_id,actor=actor,workspace=actor.workspace).first()
    if not draft:raise ValidationError('This review belongs to another account or household.')
    if not confirmed:raise ValidationError('Confirm the reviewed quantities, costs and participants before saving.')
    if draft.confirmed_ids:return draft.confirmed_ids
    if timezone.now()-draft.created_at>timezone.timedelta(hours=24):raise ValidationError('This review expired. Scan the receipts again.')
    source=draft.payload['receipts'];expected={r['line_id'] for rec in source for r in rec['rows']}
    if len(rows)!=len(expected) or {r.get('line_id') for r in rows}!=expected:raise ValidationError('The receipt lines changed. Reload the review.')
    edited={r['line_id']:r for r in rows};units=defaultdict(int);items={};prepared=[]
    for receipt in source:
        if PurchaseReceipt.objects.filter(workspace=actor.workspace,fingerprint=receipt['fingerprint']).exists():raise ValidationError('A receipt in this review was already saved. Nothing was added.')
        payer=Membership.objects.filter(pk=receipt['payer_id'],workspace=actor.workspace,is_active=True, user__is_active=True).first()
        if not payer:raise ValidationError('The payer is no longer active in this household.')
        verified=[]
        for original in receipt['rows']:
            row=edited[original['line_id']];item_id=row.get('item_id');qty=row.get('quantity');amount=row.get('amount_cents')
            if type(qty) is not int or not 1<=qty<=1000 or type(amount) is not int or not 0<amount<=99999999:
                raise ValidationError('Resolve every item match, positive amount and quantity.')
            recipient_ids=row.get('recipient_ids',[])
            if item_id is None:
                if not isinstance(recipient_ids,list) or not recipient_ids or any(type(pk) is not int for pk in recipient_ids) or len(set(recipient_ids))!=len(recipient_ids):
                    raise ValidationError('Choose one or more roommate baskets for every unmatched item.')
                recipients=list(Membership.objects.filter(workspace=actor.workspace,is_active=True,user__is_active=True,user__isnull=False,pk__in=recipient_ids).order_by('pk'))
                if len(recipients)!=len(recipient_ids):raise ValidationError('Choose active roommates from this household only.')
                all_ids=set(Membership.objects.filter(workspace=actor.workspace,is_active=True,user__is_active=True,user__isnull=False).values_list('pk',flat=True))
                item=PurchaseItem.objects.create(workspace=actor.workspace,requested_by=recipients[0],name=original['name'][:120],quantity=qty,scope='household' if set(recipient_ids)==all_ids else 'personal')
                PurchaseClaim.objects.bulk_create([PurchaseClaim(item=item,member=person,kind='shared') for person in recipients])
                item_id=item.pk;items[item_id]=item
            elif type(item_id) is not int or recipient_ids:
                raise ValidationError('Choose an existing list item or roommate baskets, not both.')
            item=items.get(item_id)
            if not item:
                item=PurchaseItem.objects.filter(pk=item_id,workspace=actor.workspace,state='open').prefetch_related('claims__member').first()
                if not item or draft.payload['versions'].get(str(item.pk))!=item.version:raise ValidationError('A list item or its participants changed. Start a fresh receipt review.')
                if any(not claim.member.is_active for claim in item.claims.all()):raise ValidationError('A participant is no longer active. Resolve their list item before purchasing.')
                items[item_id]=item
            units[item_id]+=qty;verified.append({'item':item,'quantity':qty,'amount_cents':amount,'line_id':row['line_id']})
        subtotal=sum(r['amount_cents'] for r in verified)
        if subtotal+receipt['tax_cents']-receipt['discount_cents']!=receipt['total_cents']:
            raise ValidationError('Receipt items + tax − discount must exactly equal the receipt total. Correct the text or totals and start a new review.')
        adjusted=weighted_shares(receipt['total_cents'],{r['line_id']:Decimal(r['amount_cents']) for r in verified})
        if any(v<=0 for v in adjusted.values()):raise ValidationError('Discounts cannot reduce a receipt line to zero. Remove free items before reviewing.')
        prepared.append((receipt,payer,verified,adjusted))
    for item_id,quantity in units.items():
        item = items[item_id]
        has_own_units = item.claims.filter(kind='own').exists()
        if quantity < item.total_units or (has_own_units and quantity != item.total_units):
            raise ValidationError(f'{item.name}: receipts contain {quantity} units, but the list requests {item.total_units}. Include all requested units; for individual own-unit requests, quantities must match exactly.')
    ids=[]
    for receipt,payer,verified,adjusted in prepared:
        saved=PurchaseReceipt.objects.create(workspace=actor.workspace,submitted_by=actor,fingerprint=receipt['fingerprint'],total_cents=receipt['total_cents'],draft=draft)
        for row in verified:
            item=row['item'];amount=adjusted[row['line_id']];shares=weighted_shares(amount,{k:Decimal(v) for k,v in claim_weights(item).items()})
            expense=save_expense(actor,{'amount':Decimal(amount)/100,'paid_by':payer,'title':item.name,'date':receipt['date'],'category':'groceries','split_method':'custom',
                'note':f'Reviewed receipt · {row["quantity"]} units. Shared-unit and own-unit costs allocated across this purchase group. Tax and discount allocated proportionally.',
                'split_data':{'purchase_item':item.pk}},shares,uuid.uuid5(uuid.NAMESPACE_URL,f'hestia-receipt:{draft.pk}:{row["line_id"]}'))
            ReceiptPurchaseLine.objects.create(receipt=saved,item=item,quantity=row['quantity'],expense=expense);ids.append(expense.pk)
    for item in items.values():item.state='purchased';item.is_checked=True;item.version+=1;item.save(update_fields=['state','is_checked','version'])
    draft.confirmed_ids=ids;draft.save(update_fields=['confirmed_ids']);return ids


@transaction.atomic
def check_item(actor,item_id,checked):
    actor=lock_household(actor)
    item=PurchaseItem.objects.filter(pk=item_id,workspace=actor.workspace).first()
    if not item:raise ValidationError('Choose an item in this household.')
    if item.state!='open':raise ValidationError('Receipt-confirmed items cannot be unchecked. Their expenses are managed in the shared tab.')
    item.is_checked=bool(checked)
    item.save(update_fields=['is_checked'])
    return item
