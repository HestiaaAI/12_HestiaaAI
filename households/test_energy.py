from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from households.energy import outdoor_temperatures, recommend_temperature
from households.models import Membership, ThermostatPreference, Workspace


class ThermostatPlannerTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name="Maple House", weather_location="Champaign, Illinois")
        users = get_user_model().objects
        self.sam = users.create_user(username="sam")
        self.alex = users.create_user(username="alex")
        self.sam_membership = Membership.objects.create(
            user=self.sam, workspace=self.workspace, display_name="Sam", role=Membership.MemberRole.OWNER,
        )
        self.alex_membership = Membership.objects.create(
            user=self.alex, workspace=self.workspace, display_name="Alex",
        )
        self.url = reverse("groceries:energy", args=[self.workspace.pk])

    @patch("inventory.views.outdoor_temperatures", return_value=[30, 34, 31])
    @patch("inventory.views.find_location", return_value={"label": "Champaign, Illinois"})
    def test_roommates_save_separate_ranges_and_get_an_overnight_recommendation(self, location, weather):
        for user, low, high in ((self.sam, 66, 72), (self.alex, 69, 74)):
            self.client.force_login(user)
            response = self.client.post(self.url, {
                "action": "preferences", "day_min": 68, "day_max": 77,
                "night_min": low, "night_max": high,
            })
            self.assertRedirects(response, self.url)
        response = self.client.get(self.url, {"period": "night"})
        self.assertContains(response, "69°F")
        self.assertContains(response, "Within every submitted range")
        weather.assert_called_once_with(location.return_value, "night")

    def test_outsider_access_and_invalid_range(self):
        self.client.force_login(self.sam)
        response = self.client.post(self.url, {
            "action": "preferences", "day_min": 76, "day_max": 68, "night_min": 66, "night_max": 72,
        })
        self.assertContains(response, "Enter a maximum at or above the minimum.")
        self.assertFalse(ThermostatPreference.objects.exists())
        self.client.force_login(self.alex)
        self.assertEqual(self.client.post(self.url, {"action": "location", "location": "Chicago"}).status_code, 404)
        self.client.force_login(get_user_model().objects.create_user(username="outsider"))
        self.assertRedirects(self.client.get(self.url), reverse("households:onboarding"), fetch_redirect_response=False)

    def test_weather_affects_shared_range_and_conflicts_minimize_worst_miss(self):
        self.assertEqual(recommend_temperature([(66, 72), (69, 74)], [30, 34]), 69)
        self.assertEqual(recommend_temperature([(66, 72), (69, 74)], [88, 92]), 72)
        self.assertEqual(recommend_temperature([(60, 66), (72, 75)], [29]), 69)

    @patch("households.energy.timezone.now", return_value=datetime(2026, 11, 12, 0, tzinfo=timezone.utc))
    @patch("households.energy._get_weather")
    def test_overnight_weather_crosses_midnight_in_location_timezone(self, weather, now):
        def timestamp(hour):
            return int(datetime(2026, 11, 12, hour, tzinfo=timezone.utc).timestamp())

        cache.clear()
        self.addCleanup(cache.clear)
        weather.return_value = {
            "timezone": "America/Chicago",
            "hourly": {"time": [timestamp(hour) for hour in (3, 4, 11, 12)],
                       "temperature_2m": [42, 40, 33, 32]},
        }
        self.assertEqual(outdoor_temperatures({"latitude": 40.1, "longitude": -88.2}, "night"), [40, 33])
