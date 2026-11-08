"""Question input for the handbook Q&A page."""

from django import forms

from workflows.services.ask_hestia import MAX_QUESTION_CHARS


class AskHestiaForm(forms.Form):
    question = forms.CharField(
        label="Your household question",
        max_length=MAX_QUESTION_CHARS,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Where do we keep the shared cordless drill?"}),
    )
