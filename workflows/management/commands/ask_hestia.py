"""Exercise the same Ask Hestia service that the Django page will call."""

import json

from django.core.management.base import BaseCommand, CommandError

from workflows.services.ask_hestia import AskHestiaError, answer_question


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+")

    def handle(self, *args, **options):
        for question in options["question"]:
            try:
                result = answer_question(question)
            except AskHestiaError as exc:
                raise CommandError(f"{exc.code}: {exc}") from exc
            self.stdout.write(json.dumps({"question": question, **result}, ensure_ascii=False))
