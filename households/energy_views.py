"""Thermostat recommendations for the selected household."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .context import fresh_household, require_household
from .energy import WeatherUnavailable, find_location, outdoor_temperatures, recommend_temperature
from .energy_forms import ThermostatPreferenceForm, WeatherLocationForm
from .models import Membership, ThermostatPreference
from .services import HouseholdError, locked_household, require_owner


@login_required
@require_http_methods(["GET", "POST"])
def planner(request, workspace_id):
    actor = require_household(request)
    if actor.workspace_id != workspace_id:
        raise Http404

    workspace = actor.workspace
    can_set_location = actor.role == Membership.MemberRole.OWNER
    preference = ThermostatPreference.objects.filter(membership=actor).first()
    preferences_form = ThermostatPreferenceForm(instance=preference)
    location_form = WeatherLocationForm(initial={"location": workspace.weather_location})
    period = request.GET.get("period")
    if period not in ("day", "night"):
        period = None

    if request.method == "POST":
        try:
            action = request.POST.get("action")
            if action == "preferences":
                preferences_form = ThermostatPreferenceForm(request.POST, instance=preference)
                if preferences_form.is_valid():
                    with transaction.atomic():
                        _, current, _ = locked_household(actor)
                        ThermostatPreference.objects.update_or_create(
                            membership=current, defaults=preferences_form.cleaned_data,
                        )
                    messages.success(request, "Your comfort ranges are saved.")
                    return redirect("households:energy", workspace_id=workspace_id)
            elif action == "location":
                require_owner(actor)
                location_form = WeatherLocationForm(request.POST)
                if location_form.is_valid():
                    query = location_form.cleaned_data["location"]
                    try:
                        require_owner(fresh_household(request))
                        location = find_location(query)
                    except WeatherUnavailable as exc:
                        location_form.add_error("location", str(exc))
                    else:
                        with transaction.atomic():
                            current_workspace, current, _ = locked_household(actor)
                            require_owner(current)
                            current_workspace.weather_location = query
                            current_workspace.save(update_fields=["weather_location", "updated_at"])
                        messages.success(request, f"Weather location set to {location['label']}.")
                        return redirect("households:energy", workspace_id=workspace_id)
            else:
                raise Http404
        except HouseholdError as exc:
            raise PermissionDenied(str(exc)) from exc

    roommates = Membership.objects.filter(workspace=workspace, is_active=True, user__is_active=True)
    preferences = list(ThermostatPreference.objects.filter(membership__in=roommates)
                       .select_related("membership").order_by("membership__display_name", "pk"))
    recommendation = None
    weather_error = ""
    if request.method == "GET" and period and preferences and workspace.weather_location:
        try:
            recommendation = _recommendation(request, preferences, period)
        except WeatherUnavailable as exc:
            weather_error = str(exc)
    return render(request, "households/energy.html", {
        "workspace": workspace, "can_set_location": can_set_location,
        "preferences_form": preferences_form, "location_form": location_form,
        "responses": len(preferences), "roommate_count": roommates.count(), "period": period,
        "recommendation": recommendation, "weather_error": weather_error,
    })


def _recommendation(request, preferences, period):
    query = fresh_household(request).workspace.weather_location
    if not query:
        return None
    location = find_location(query)
    if fresh_household(request).workspace.weather_location != query:
        raise WeatherUnavailable("The household weather location changed. Try again.")
    temperatures = outdoor_temperatures(location, period)
    if fresh_household(request).workspace.weather_location != query:
        raise WeatherUnavailable("The household weather location changed. Try again.")
    ranges = [(getattr(item, f"{period}_min"), getattr(item, f"{period}_max"))
              for item in preferences]
    setpoint = recommend_temperature(ranges, temperatures)
    return {
        "setpoint": setpoint,
        "location": location["label"],
        "outdoor_low": min(temperatures),
        "outdoor_high": max(temperatures),
        "outside_ranges": [
            {"name": item.membership.display_name, "low": low, "high": high}
            for item, (low, high) in zip(preferences, ranges)
            if not low <= setpoint <= high
        ],
    }
