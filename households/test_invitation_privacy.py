import logging
import sys
from io import StringIO
from contextlib import redirect_stdout
from urllib.parse import quote
from django.test import TestCase,RequestFactory,override_settings
from .test_invitations import InvitationFixture
from .invitation_privacy import InvitationLogFilter

class InvitationPrivacyTests(InvitationFixture,TestCase):
    def test_raw_encoded_paths_and_error_report_payload_are_redacted(self):
        token='synthetic-token-'+('x'*32)
        path='/households/invites/'+token+'/'
        request=RequestFactory().post(path,{'email':'private@example.test','nonce':token})
        request.META['HTTP_COOKIE']='private-session'
        try:raise ValueError('Synthetic diagnostic')
        except ValueError:info=sys.exc_info()
        record=logging.LogRecord('django.request',logging.ERROR,'fixture',1,'Failure %s %s',(path,'private@example.test'),info)
        record.request=request
        InvitationLogFilter().filter(record)
        self.assertNotIn(token,record.getMessage())
        self.assertNotIn('private@example.test',record.getMessage())
        self.assertNotIn(token,record.request.get_full_path())
        self.assertNotIn('private@example.test',str(record.request.POST))
        self.assertIsNone(record.exc_info)
        self.assertEqual(record.request.META['HTTP_COOKIE'],'[redacted]')
        # The actual request is never mutated by the log filter.
        self.assertEqual(request.path,path)
        encoded=logging.LogRecord('django.server',logging.INFO,'fixture',1,'GET /accounts/signup/?next=%s',(quote(path,safe=''),),None)
        InvitationLogFilter().filter(encoded)
        self.assertNotIn(token,encoded.getMessage())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_email_does_not_print_invitation_token_or_recipient(self):
        output=StringIO()
        with redirect_stdout(output),self.captureOnCommitCallbacks(execute=True):
            invitation,token=self.issue()
        self.assertEqual(invitation.delivery_status,'copy_only')
        self.assertNotIn(token,output.getvalue())
        self.assertNotIn(self.roommate.email,output.getvalue())

class PrivateInvitationFormTests(TestCase):
    def test_private_forms_keep_csrf_and_load_only_local_submission_handler(self):
        from .invitation_acceptance import private_invitation_response
        from django.http import HttpResponse
        response=private_invitation_response(HttpResponse())
        self.assertIn("script-src 'self'",response['Content-Security-Policy'])
        from django.template.loader import get_template
        for name in ['households/invites.html','households/accept_invite.html']:
            source=get_template(name).template.source
            self.assertIn('js/invitation-forms.js',source)
