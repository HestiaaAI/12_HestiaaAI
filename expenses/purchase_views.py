from decimal import Decimal
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST,require_http_methods
from .views import membership,page_context
from .models import PurchaseItem,ReceiptDraft
from .purchases import create_item,join_item,prepare_receipts,confirm_receipts,check_item
from .purchase_forms import PurchaseItemForm,JoinPurchaseForm,ReceiptInputFormSet,ReceiptLineFormSet


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def purchase_list(request,workspace_id):
    actor=membership(request,workspace_id)
    form=PurchaseItemForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        try:create_item(actor,**form.cleaned_data)
        except (ValidationError,OperationalError) as error:
            form.add_error(None,error if isinstance(error,ValidationError) else 'The list is busy. Try again.')
        else:
            messages.success(request,'Added to your household’s visible purchase lists.')
            return redirect('groceries:shopping',workspace_id=workspace_id)
    active_member_ids=set(actor.workspace.memberships.select_related('user__hestia_avatar').filter(is_active=True,user__is_active=True).values_list('pk',flat=True))
    rows=[]
    for item in PurchaseItem.objects.filter(workspace=actor.workspace).prefetch_related('claims__member__user__hestia_avatar','requested_by__user__hestia_avatar')[:200]:
        claims=list(item.claims.all());participants=[claim.member for claim in claims]
        rows.append({'item':item,'claims':claims,'group_label':' + '.join(p.display_name for p in participants),
                     'group_key':','.join(str(pk) for pk in sorted(p.pk for p in participants)),
                     'can_join':item.state=='open' and actor.pk not in [c.member_id for c in claims],
                     'bucket':'household' if item.scope=='household' or (len(active_member_ids)>1 and {claim.member_id for claim in claims}==active_member_ids) else 'shared' if len(claims)>1 else 'personal'})
    from .models import Expense
    group=request.GET.get('group','');view=request.GET.get('view','all');active_group='';group_expenses=[]
    if group:
        matching=[row for row in rows if row['group_key']==group]
        if matching:
            active_group=matching[0]['group_label']
            group_expenses=Expense.objects.filter(workspace=actor.workspace,voided_at=None,purchase_line__item_id__in=[row['item'].pk for row in matching])
        rows=matching
    elif view in ('household','personal','shared'):rows=[row for row in rows if row['bucket']==view]
    board_household=[row for row in rows if row['bucket']=='household']
    board_personal=[{'member':p,'rows':[row for row in rows if row['bucket']=='personal' and row['item'].requested_by_id==p.pk]} for p in actor.workspace.memberships.select_related('user__hestia_avatar').filter(is_active=True,user__is_active=True)]
    groups={}
    for row in rows:
        if row['bucket']=='shared':
            groups.setdefault(row['group_key'],{'key':row['group_key'],'title':row['group_label'],'rows':[]})['rows'].append(row)
    board_groups=list(groups.values())
    return render(request,'expenses/purchases.html',{**page_context(actor),'rows':rows,'board_household':board_household,'board_personal':board_personal,'board_groups':board_groups,'view':view,'form':form,'join_form':JoinPurchaseForm(),'active_group':active_group,'group_expenses':group_expenses,'sections':[{'key':key,'title':title,'rows':[row for row in rows if row['bucket']==key]} for key,title in [('household','For the whole home'),('personal','Personal lists'),('shared','Sharing a little something')]]})


@login_required
@require_POST
def join_purchase(request,workspace_id,item_id):
    actor=membership(request,workspace_id)
    get_object_or_404(PurchaseItem,workspace=actor.workspace,pk=item_id)
    form=JoinPurchaseForm(request.POST)
    if form.is_valid():
        try:join_item(actor,item_id,**form.cleaned_data)
        except (ValidationError,OperationalError) as error:messages.error(request,' '.join(error.messages) if isinstance(error,ValidationError) else 'The list is busy. Try again.')
        else:messages.success(request,'You’re included. The quantity and split have been updated.')
    else:messages.error(request,'Choose a join option and a quantity from 1 to 1000.')
    return redirect('groceries:shopping',workspace_id=workspace_id)


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def receipt_upload(request,workspace_id):
    actor=membership(request,workspace_id)
    forms=ReceiptInputFormSet(request.POST if request.method=='POST' else None,prefix='receipts',form_kwargs={'workspace':actor.workspace,'actor':actor},initial=[{}])
    error=''
    if request.method=='POST' and forms.is_valid():
        use_ai=request.POST.get('matching','ai')!='local'
        if use_ai and settings.GROQ_API_KEY.strip() and not cache.add(f'purchase-ai:{request.user.pk}',True,timeout=20):
            error='Wait a moment before requesting AI matching again, or use local matching.'
        else:
            try:draft=prepare_receipts(actor,[f.cleaned_data for f in forms],use_ai=use_ai)
            except (ValidationError,OperationalError) as exc:error=' '.join(exc.messages) if isinstance(exc,ValidationError) else 'The review could not be saved. Try again.'
            else:return redirect('groceries:receipt-split-review',workspace_id=workspace_id,draft_id=draft.pk)
    return render(request,'expenses/receipt_upload.html',{**page_context(actor),'forms':forms,'matching_mode':'local' if request.POST.get('matching')=='local' else 'ai','error':error})


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def receipt_review(request,workspace_id,draft_id):
    actor=membership(request,workspace_id)
    draft=get_object_or_404(ReceiptDraft,pk=draft_id,workspace=actor.workspace,actor=actor)
    if draft.confirmed_ids:
        messages.info(request,'This review was already saved. No duplicate expenses were added.')
        return redirect('expenses:overview',workspace_id=workspace_id)
    rows=[r for receipt in draft.payload['receipts'] for r in receipt['rows']]
    initial=[{'line_id':r['line_id'],'item':r['item_id'],'quantity':r['quantity'],'amount':Decimal(r['amount_cents'])/100} for r in rows]
    forms=ReceiptLineFormSet(request.POST if request.method=='POST' else None,initial=initial,prefix='lines',form_kwargs={'draft':draft})
    error=''
    if request.method=='POST' and forms.is_valid():
        reviewed=[{'line_id':f.cleaned_data['line_id'],'item_id':f.cleaned_data['item'].pk if f.cleaned_data['item'] else None,'recipient_ids':list(f.cleaned_data['recipients'].values_list('pk',flat=True)),'quantity':f.cleaned_data['quantity'],'amount_cents':int(f.cleaned_data['amount']*100)} for f in forms]
        try:ids=confirm_receipts(actor,draft.pk,reviewed,request.POST.get('confirm')=='on')
        except (ValidationError,OperationalError) as exc:error=' '.join(exc.messages) if isinstance(exc,ValidationError) else 'The household is being updated. Try again.'
        else:
            messages.success(request,f'{len(ids)} reviewed expense lines saved. Purchased lists and balances are updated.')
            return redirect('expenses:overview',workspace_id=workspace_id)
    members={p.pk:p for p in actor.workspace.memberships.all()}
    receipts=[{**receipt,'payer':members.get(receipt['payer_id'])} for receipt in draft.payload['receipts']]
    candidates=PurchaseItem.objects.filter(workspace=actor.workspace,pk__in=draft.payload['versions']).prefetch_related('claims__member')
    from .purchases import claim_weights
    preview_data={}
    for item in candidates:
        try:
            weights=claim_weights(item)
        except ValidationError:
            error = (error+' ' if error else '') + f'“{item.name}” has no participants. Return to the shopping list and choose who is sharing it before saving.'
            weights={}
        preview_data[str(item.pk)]={'weights':{str(k):v for k,v in weights.items()},'names':{str(c.member_id):c.member.display_name for c in item.claims.all()}}

    return render(request,'expenses/receipt_review.html',{**page_context(actor),'draft':draft,'forms':forms,'receipts':receipts,'candidates':candidates,'receipt_preview':{str(i+1):{k:receipt[k] for k in ('total_cents','tax_cents','discount_cents')} for i,receipt in enumerate(receipts)},'preview_data':preview_data,'basket_members':actor.workspace.memberships.filter(is_active=True,user__isnull=False),'error':error})


@login_required
@require_POST
def check_purchase(request,workspace_id,item_id):
    actor=membership(request,workspace_id)
    get_object_or_404(PurchaseItem,workspace=actor.workspace,pk=item_id)
    try:
        item=check_item(actor,item_id,request.POST.get('checked')=='on')
    except (ValidationError,OperationalError) as error:
        text=' '.join(error.messages) if isinstance(error,ValidationError) else 'The list is busy. Try again.'
        if request.headers.get('X-Requested-With')=='XMLHttpRequest':return JsonResponse({'error':text},status=400)
        messages.error(request,text)
    else:
        if request.headers.get('X-Requested-With')=='XMLHttpRequest':return JsonResponse({'checked':item.is_checked})
    return redirect('groceries:shopping',workspace_id=workspace_id)
