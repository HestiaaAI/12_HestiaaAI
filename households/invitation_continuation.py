"""Only validated local invitation destinations survive the account lifecycle."""
import re
from urllib.parse import urlsplit
from django.urls import resolve, Resolver404

INVITE_NEXT = 'household_invite_next'


def validated_invite_next(value):
    if not isinstance(value,str):
        return None
    try:
        parts=urlsplit(value)
    except ValueError:
        return None
    if parts.scheme or parts.netloc or parts.query or parts.fragment or not value.startswith('/') or value.startswith('//'):
        return None
    try:
        match=resolve(parts.path)
    except Resolver404:
        return None
    if match.view_name == 'households:accept-invite' and re.fullmatch(r'[A-Za-z0-9_-]{43,128}',match.kwargs['token']):
        return parts.path


def invitation_next(request):
    for value in (request.POST.get('next'),request.GET.get('next'),request.session.get(INVITE_NEXT)):
        path=validated_invite_next(value)
        if path:
            if request.session.get(INVITE_NEXT) != path:
                request.session[INVITE_NEXT]=path
            return path
    return None
