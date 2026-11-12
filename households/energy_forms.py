from django import forms

from .models import ThermostatPreference


class ThermostatPreferenceForm(forms.ModelForm):
    class Meta:
        model = ThermostatPreference
        fields = ("day_min", "day_max", "night_min", "night_max")
        labels = {
            "day_min": "Daytime minimum (°F)", "day_max": "Daytime maximum (°F)",
            "night_min": "Overnight minimum (°F)", "night_max": "Overnight maximum (°F)",
        }

    def clean(self):
        data = super().clean()
        for period in ("day", "night"):
            minimum, maximum = f"{period}_min", f"{period}_max"
            if minimum in data and maximum in data and data[minimum] > data[maximum]:
                self.add_error(maximum, "Enter a maximum at or above the minimum.")
        return data


class WeatherLocationForm(forms.Form):
    location = forms.CharField(
        label="Household city or postal code", max_length=80, min_length=2,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Champaign, Illinois"}),
    )
