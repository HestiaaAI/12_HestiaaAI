from django.core.management.base import BaseCommand
from expenses.reminders import collect_reminders,send_pending
class Command(BaseCommand):
    help='Collect due bill reminders and send unsent web-push notifications. Run every 15 minutes.'
    def add_arguments(self,parser):
        parser.add_argument("--watch",action="store_true",help="Keep checking once per minute for local testing.")
    def handle(self,*args,**kwargs):
        if kwargs.get("watch"):
            import time
            while True:
                self.handle(watch=False)
                time.sleep(60)
            return
        count=collect_reminders();result=send_pending()
        self.stdout.write(f"In-app reminders created: {count}; push sent: {result['sent']}; failed: {result['failed']}; configured: {result['configured']}")
