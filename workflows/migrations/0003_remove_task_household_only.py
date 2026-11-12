from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("workflows", "0002_task_household_only")]
    operations = [migrations.RemoveField(model_name="task", name="household_only")]
