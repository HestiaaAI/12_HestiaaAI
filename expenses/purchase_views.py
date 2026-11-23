from decimal import Decimal
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST,require_http_methods
from .views import membership,page_context
from .models import ReceiptDraft
from .policies import visible_expenses, visible_items, visible_lists
from .purchases import create_item,join_item,prepare_receipts,confirm_receipts,check_item,validate_receipt_audiences
from .purchase_forms import PurchaseItemForm,JoinPurchaseForm,ReceiptInputFormSet,ReceiptLineFormSet


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def purchase_list(request,workspace_id,list_id=None):
    actor=membership(request,workspace_id)
    shopping_list = get_object_or_404(visible_lists(actor=actor).select_related("circle"), pk=list_id) if list_id else None
    form=PurchaseItemForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        try:create_item(actor,**form.cleaned_data,purchase_list=shopping_list,audience=request.POST.get("audience", "") if shopping_list else None)
        except (ValidationError,OperationalError) as error:
            form.add_error(None,error if isinstance(error,ValidationError) else 'The list is busy. Try again.')
        else:
            messages.success(request,'Added to your household’s visible purchase lists.')
            if shopping_list:
                return redirect('groceries:named-list', workspace_id=workspace_id, list_id=shopping_list.pk)
            return redirect('groceries:shopping',workspace_id=workspace_id)
    from households.sharing import active_readers
    readers = active_readers(actor.workspace, shopping_list.circle if shopping_list else None).select_related('user__hestia_avatar')
    active_member_ids = set(readers.values_list('pk', flat=True))
    rows=[]
    items = visible_items(actor=actor)
    items = items.filter(list=shopping_list) if shopping_list else items.filter(list__is_default=True)
    for item in items.prefetch_related('claims__member__user__hestia_avatar','requested_by__user__hestia_avatar')[:200]:
        claims=list(item.claims.all());participants=[claim.member for claim in claims]
        rows.append({'item':item,'claims':claims,'total_units':item.quantity + sum(claim.quantity for claim in claims if claim.kind == 'own'),'group_label':' + '.join(p.display_name for p in participants),
                     'group_key':','.join(str(pk) for pk in sorted(p.pk for p in participants)),
                     'can_join':item.state=='open' and actor.pk not in [c.member_id for c in claims],
                     'bucket':'household' if item.scope=='household' or (len(active_member_ids)>1 and {claim.member_id for claim in claims}==active_member_ids) else 'shared' if len(claims)>1 else 'personal'})
    group=request.GET.get('group','');view=request.GET.get('view','all');active_group='';group_expenses=[]
    if group:
        matching=[row for row in rows if row['group_key']==group]
        if matching:
            active_group=matching[0]['group_label']
            group_expenses=visible_expenses(actor=actor).filter(voided_at=None,purchase_line__item_id__in=[row['item'].pk for row in matching])
        rows=matching
    elif view in ('household','personal','shared'):rows=[row for row in rows if row['bucket']==view]
    board_household=[row for row in rows if row['bucket']=='household']
    board_personal=[{'member':p,'rows':[row for row in rows if row['bucket']=='personal' and row['item'].requested_by_id==p.pk]} for p in readers]
    groups={}
    for row in rows:
        if row['bucket']=='shared':
            groups.setdefault(row['group_key'],{'key':row['group_key'],'title':row['group_label'],'rows':[]})['rows'].append(row)
    board_groups=list(groups.values())
    return render(request,'expenses/purchases.html',{**page_context(actor),'shopping_list':shopping_list,'named_lists':visible_lists(actor=actor).filter(is_default=False),'rows':rows,'board_household':board_household,'board_personal':board_personal,'board_groups':board_groups,'view':view,'form':form,'join_form':JoinPurchaseForm(),'active_group':active_group,'group_expenses':group_expenses,'sections':[{'key':key,'title':title,'rows':[row for row in rows if row['bucket']==key]} for key,title in [('household','For the whole home'),('personal','Personal lists'),('shared','Sharing a little something')]]})


@login_required
@require_POST
def join_purchase(request,workspace_id,item_id):
    actor=membership(request,workspace_id)
    target = get_object_or_404(visible_items(actor=actor).select_related('list'),pk=item_id)
    form=JoinPurchaseForm(request.POST)
    if form.is_valid():
        try:join_item(actor,item_id,**form.cleaned_data)
        except (ValidationError,OperationalError) as error:messages.error(request,' '.join(error.messages) if isinstance(error,ValidationError) else 'The list is busy. Try again.')
        else:messages.success(request,'You’re included. The quantity and split have been updated.')
    else:messages.error(request,'Choose a join option and a quantity from 1 to 1000.')
    if target.list_id and not target.list.is_default:
        return redirect('groceries:named-list', workspace_id=workspace_id, list_id=target.list_id)
    return redirect('groceries:shopping',workspace_id=workspace_id)


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def receipt_upload(request,workspace_id):
    actor=membership(request,workspace_id)
    target_id = request.GET.get("list")
    if target_id and not target_id.isdecimal():
        raise Http404
    target = get_object_or_404(visible_lists(actor=actor).select_related("circle"), pk=target_id) if target_id else None
    forms=ReceiptInputFormSet(request.POST if request.method=='POST' else None,prefix='receipts',form_kwargs={'workspace':actor.workspace,'actor':actor,'circle':target.circle if target else None},initial=[{}])
    error=''
    if request.method == "POST" and target and request.POST.get("audience") != f"{target.circle_id}:{target.circle.version}":
        error = "Sharing changed. Reload before scanning."
    elif request.method=='POST' and forms.is_valid():
        use_ai=request.POST.get('matching','ai')!='local'
        if use_ai and settings.GROQ_API_KEY.strip() and not cache.add(f'purchase-ai:{request.user.pk}',True,timeout=20):
            error='Wait a moment before requesting AI matching again, or use local matching.'
        else:
            try:draft=prepare_receipts(actor,[f.cleaned_data for f in forms],use_ai=use_ai,purchase_list=target)
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
    if timezone.now() - draft.created_at > timezone.timedelta(hours=24):
        messages.error(request, "This review expired. Start a fresh receipt review.")
        return redirect("groceries:receipt-split", workspace_id=workspace_id)
    try:
        validate_receipt_audiences(actor, draft)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("groceries:receipt-split", workspace_id=workspace_id)
    rows=[r for receipt in draft.payload['receipts'] for r in receipt['rows']]
    initial=[{'line_id':r['line_id'],'item':r['item_id'],'quantity':r['quantity'],'amount':Decimal(r['amount_cents'])/100} for r in rows]
    forms=ReceiptLineFormSet(request.POST if request.method=='POST' else None,initial=initial,prefix='lines',form_kwargs={'draft':draft})
    error=''
    if request.method=='POST' and forms.is_valid():
        reviewed=[{'line_id':f.cleaned_data['line_id'],'list_id':f.cleaned_data['destination'].pk if f.cleaned_data['destination'] else None,'item_id':f.cleaned_data['item'].pk if f.cleaned_data['item'] else None,'recipient_ids':list(f.cleaned_data['recipients'].values_list('pk',flat=True)),'quantity':f.cleaned_data['quantity'],'amount_cents':int(f.cleaned_data['amount']*100)} for f in forms]
        try:ids=confirm_receipts(actor,draft.pk,reviewed,request.POST.get('confirm')=='on')
        except (ValidationError,OperationalError) as exc:error=' '.join(exc.messages) if isinstance(exc,ValidationError) else 'The household is being updated. Try again.'
        else:
            messages.success(request,f'{len(ids)} reviewed expense lines saved. Purchased lists and balances are updated.')
            return redirect('expenses:overview',workspace_id=workspace_id)
    members={p.pk:p for p in actor.workspace.memberships.all()}
    receipts=[{**receipt,'payer':members.get(receipt['payer_id'])} for receipt in draft.payload['receipts']]
    candidates=visible_items(actor=actor).filter(pk__in=draft.payload['versions']).prefetch_related('claims__member')
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
    target = get_object_or_404(visible_items(actor=actor).select_related('list'),pk=item_id)
    try:
        item=check_item(actor,item_id,request.POST.get('checked')=='on')
    except (ValidationError,OperationalError) as error:
        text=' '.join(error.messages) if isinstance(error,ValidationError) else 'The list is busy. Try again.'
        if request.headers.get('X-Requested-With')=='XMLHttpRequest':return JsonResponse({'error':text},status=400)
        messages.error(request,text)
    else:
        if request.headers.get('X-Requested-With')=='XMLHttpRequest':return JsonResponse({'checked':item.is_checked})
    if target.list_id and not target.list.is_default:
        return redirect('groceries:named-list', workspace_id=workspace_id, list_id=target.list_id)
    return redirect('groceries:shopping',workspace_id=workspace_id)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def named_list_form(request, workspace_id, list_id=None, ledger_only=False, circle_id=None):
    from django import forms
    from django.core.exceptions import PermissionDenied
    from django.db import transaction
    from households.models import Membership
    from households.sharing import Visibility, change_circle_audience, change_list_audience, create_circle, require_circle
    from .models import PurchaseList
    from .services import lock_household
    from .policies import household_circle

    actor = membership(request, workspace_id)
    purchase_list = get_object_or_404(visible_lists(actor=actor).select_related("circle"), pk=list_id) if list_id else None
    existing_circle = require_circle(actor=actor, circle_id=circle_id) if circle_id else None
    if existing_circle and (existing_circle.created_by_id != actor.pk or existing_circle.purchase_lists.exists()):
        raise PermissionDenied
    if purchase_list and (purchase_list.created_by_id != actor.pk or purchase_list.is_default):
        raise PermissionDenied

    editing = bool(purchase_list or existing_circle)

    class AudienceForm(forms.Form):
        title = forms.CharField(max_length=120, label="Expense group name" if ledger_only else "List name", required=not editing)
        visibility = forms.ChoiceField(label="Who can see this?", choices=Visibility.choices)
        readers = forms.ModelMultipleChoiceField(
            label="Selected roommates", required=False, widget=forms.CheckboxSelectMultiple,
            queryset=Membership.objects.filter(workspace=actor.workspace, is_active=True, user__is_active=True).exclude(pk=actor.pk),
        )
        audience = forms.CharField(widget=forms.HiddenInput, required=editing)
        confirm = forms.BooleanField(label="Confirm this audience", required=True)

    initial = {"visibility": Visibility.HOUSEHOLD}
    if editing:
        source = purchase_list.circle if purchase_list else existing_circle
        initial = {
            "visibility": source.visibility,
            "audience": f"{source.pk}:{source.version}",
            "readers": source.selected_readers.exclude(pk=actor.pk),
        }
    form = AudienceForm(request.POST if request.method == "POST" else None, initial=initial)
    if editing:
        del form.fields["title"]
    if form.is_valid():
        values = form.cleaned_data
        reader_ids = [reader.pk for reader in values["readers"]]
        try:
            with transaction.atomic():
                actor = lock_household(actor)
                if editing and values["audience"] != initial["audience"]:
                    raise ValidationError("Sharing changed. Reload before trying again.")
                if existing_circle:
                    circle = change_circle_audience(
                        actor=actor, circle_id=existing_circle.pk, visibility=values["visibility"],
                        member_ids=reader_ids, expected_version=existing_circle.version,
                    )
                elif purchase_list:
                    change_list_audience(
                        actor=actor, list_id=purchase_list.pk, visibility=values["visibility"],
                        member_ids=reader_ids, expected_version=purchase_list.circle.version,
                        expected_circle=purchase_list.circle_id,
                    )
                else:
                    if values["visibility"] == Visibility.HOUSEHOLD and reader_ids:
                        raise ValidationError("Clear selected roommates to share with everyone.")
                    circle = household_circle(actor.workspace) if values["visibility"] == Visibility.HOUSEHOLD else create_circle(
                        actor=actor, name=values["title"], visibility=values["visibility"], member_ids=reader_ids,
                    )
                    if not ledger_only:
                        purchase_list = PurchaseList.objects.create(
                            workspace=actor.workspace, circle=circle, title=values["title"], created_by=actor,
                        )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            if ledger_only:
                from .views import ledger_redirect
                return ledger_redirect("expenses:add", workspace_id, circle)
            return redirect("groceries:named-list", workspace_id=workspace_id, list_id=purchase_list.pk)
    return render(request, "expenses/audience_form.html", {
        **page_context(actor), "form": form, "purchase_list": purchase_list, "ledger_only": ledger_only, "existing_circle": existing_circle,
    })
