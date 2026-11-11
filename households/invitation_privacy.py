"""Redact invitation bearer paths from Django logs and error-report requests."""
import copy
import logging
import re
from django.http import QueryDict

PATH = re.compile(r'(/households/invites/)[^/?\s]+(/?)',re.I)
ENCODED_PATH = re.compile(r'(%2fhouseholds%2finvites%2f)[^%&\s]+(%2f)',re.I)
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[\w-]+')


def scrub(value, *, private=False):
    value=PATH.sub(r'\1[redacted]\2',str(value))
    value=ENCODED_PATH.sub(r'\1[redacted]\2',value)
    return EMAIL.sub('[email redacted]',value) if private else value


class InvitationLogFilter(logging.Filter):
    def filter(self,record):
        request=getattr(record,'request',None)
        message=record.getMessage()
        path=getattr(request,'path','')
        private=bool(PATH.search(message) or ENCODED_PATH.search(message) or PATH.search(path) or '/households/current/invites/' in path)
        record.msg=scrub(message,private=private)
        record.args=()
        if private:
            # Traceback locals/exception values may contain the raw bearer or
            # recipient. Retain the safe status/message, not secret stack data.
            record.exc_info=None
            record.exc_text=None
            record.stack_info=None
            if request:
                safe=copy.copy(request)
                safe.path=scrub(request.path)
                safe.path_info=scrub(request.path_info)
                safe.META={k:scrub(v,private=True) if isinstance(v,str) else v for k,v in request.META.items()}
                for key in ('HTTP_COOKIE','HTTP_AUTHORIZATION'):
                    if key in safe.META:safe.META[key]='[redacted]'
                safe._post=QueryDict('',mutable=True)
                for key in request.POST:safe._post[key]='[redacted]'
                safe.GET=QueryDict('',mutable=True)
                for key,value in request.GET.items():safe.GET[key]=scrub(value,private=True)
                safe.COOKIES={}
                safe.session={}
                safe.resolver_match=None
                from django.contrib.auth.models import AnonymousUser
                safe.user=AnonymousUser()
                record.request=safe
        return True
