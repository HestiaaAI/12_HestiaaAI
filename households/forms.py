"""Household creation fields; actor, roles and permissions stay server-owned."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django import forms


class HouseholdCreateForm(forms.Form):
    name = forms.CharField(max_length=120, label='Household name',
                           widget=forms.TextInput(attrs={'autocomplete': 'organization', 'placeholder': 'e.g. Cedar home'}))
    timezone = forms.CharField(max_length=50, initial='America/Chicago', label='Timezone',
                               help_text='Use a city timezone such as America/Chicago or Europe/London.')

    def clean_timezone(self):
        value = self.cleaned_data['timezone']
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise forms.ValidationError('Enter a valid city timezone, such as America/Chicago.')
        return value
