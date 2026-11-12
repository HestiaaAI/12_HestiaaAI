from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("households", "0002_workspace_weather_location_thermostatpreference"),
        ("households", "0003_invitation_request_nonce"),
    ]

    operations = []
