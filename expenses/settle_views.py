"""Clear settlement UI over the existing receiver-confirmed payment ledger."""
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.db.models import Q
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import Settlement
from .services import balances,transfers,original_debts,payment_plan,payment_capacity
from .views import membership,page_context

def settlement_context(actor):
    net=balances(actor.workspace)
    people={m.pk:m for m in actor.workspace.memberships.select_related('user','user__hestia_avatar').all()}
    pending=list(Settlement.objects.filter(workspace=actor.workspace,status='pending').select_related('sender__user','receiver__user'))
    outgoing=sum(p.amount_cents for p in pending if p.sender_id==actor.pk)
    incoming={}
    for p in pending:incoming[p.receiver_id]=incoming.get(p.receiver_id,0)+p.amount_cents
    options=[]
    for transfer in payment_plan(actor.workspace):
        if actor.pk not in (transfer['sender_id'],transfer['receiver_id']):continue
        sending=transfer['sender_id']==actor.pk
        other=people[transfer['receiver_id'] if sending else transfer['sender_id']]
        available=payment_capacity(actor.workspace,actor.pk,other.pk) if sending else 0
        options.append({'member':other,'amount':transfer['amount_cents'],'sending':sending,'available':min(available,transfer['amount_cents'])})
    own_pending=[p for p in pending if actor.pk in (p.sender_id,p.receiver_id)]
    groups=[]
    direct=original_debts(actor.workspace)
    for pk,person in people.items():
        details=[]
        for row in direct:
            if pk in (row['sender_id'],row['receiver_id']):
                details.append({'sender':people[row['sender_id']],'receiver':people[row['receiver_id']],'amount':row['amount_cents']})
        groups.append({'member':person,'balance':net.get(pk,0),'amount':abs(net.get(pk,0)),'details':details})
    value=net.get(actor.pk,0)
    return {'settle_net':value,'settle_amount':abs(value),'settle_options':options,'settle_pending':own_pending,'all_settled':not options and not own_pending,'household_settled':not payment_plan(actor.workspace) and not pending,'group_balances':groups,'payment_amounts':{str(p.pk):payment_capacity(actor.workspace,actor.pk,p.pk) for p in people.values() if p.pk!=actor.pk and p.is_active and p.user_id}}

@login_required
@never_cache
def settle(request,workspace_id):
    actor=membership(request,workspace_id)
    return render(request,'expenses/settle.html',{**page_context(actor),**settlement_context(actor),'show_groups':request.GET.get('view')=='balances'})


@login_required
@require_POST
@transaction.atomic
def payment_mode(request,workspace_id):
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import redirect
    from .services import lock_household
    actor=membership(request,workspace_id);lock_household(actor)
    if actor.role!='OWNER':raise PermissionDenied
    mode=request.POST.get('mode')
    if mode not in ('original','simplified'):
        messages.error(request,'Choose Original or Simplified balances.')
    elif Settlement.objects.filter(workspace=actor.workspace,status='pending').exists():
        messages.error(request,'Confirm, decline or cancel pending payments before changing the household payment mode.')
    elif mode=='original' and actor.workspace.simplify_debts and Settlement.objects.filter(workspace=actor.workspace,status='confirmed').exists() and has_debt_cycle(original_debts(actor.workspace)):
        messages.error(request,'Original mode would reintroduce circular debts after earlier simplified payments. Keep Simplified mode to avoid requesting those payments again.')
    else:
        actor.workspace.simplify_debts=mode=='simplified';actor.workspace.save(update_fields=['simplify_debts'])
        messages.success(request,'Household payment mode updated for everyone. Net balances and expense history are unchanged.')
    return redirect('expenses:settle',workspace_id=workspace_id)


def has_debt_cycle(rows):
    graph={}
    for row in rows:graph.setdefault(row['sender_id'],[]).append(row['receiver_id'])
    visiting=set();done=set()
    def visit(node):
        if node in visiting:return True
        if node in done:return False
        visiting.add(node)
        if any(visit(other) for other in graph.get(node,[])):return True
        visiting.remove(node);done.add(node)
        return False
    return any(visit(node) for node in graph if node not in done)
