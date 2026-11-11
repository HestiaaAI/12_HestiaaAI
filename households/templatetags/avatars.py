from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from households.avatars import render_avatar
from households.models import UserAvatar
register = template.Library()

@register.simple_tag
def face_avatar(person):
    user = getattr(person, 'user', person)
    if user and getattr(user, 'is_authenticated', False):
        try:
            return mark_safe(render_avatar(user.hestia_avatar.options))
        except UserAvatar.DoesNotExist:
            pass
    name = getattr(person, 'display_name', '') or (user.get_full_name() or user.get_username() if user else '')
    return format_html('<span class="avatar-initials">{}</span>', ''.join(word[0] for word in name.split()[:2]).upper() or '?')
