"""Production host configuration must work without editing Python on the server."""
import json
import os
import subprocess
import sys

from django.test import SimpleTestCase


class ProductionHostTests(SimpleTestCase):
    def hosts(self, value=None):
        environment = os.environ.copy()
        environment.pop("DJANGO_ALLOWED_HOSTS", None)
        if value is not None:
            environment["DJANGO_ALLOWED_HOSTS"] = value
        result = subprocess.run(
            [sys.executable, "-c",
             "import json; from hestia_config.settings.production import ALLOWED_HOSTS; "
             "print(json.dumps(ALLOWED_HOSTS))"],
            env=environment, capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def test_explicit_deployment_hosts_are_loaded_from_environment(self):
        self.assertEqual(
            self.hosts("hestia-demo.pythonanywhere.com,localhost,127.0.0.1"),
            ["hestia-demo.pythonanywhere.com", "localhost", "127.0.0.1"],
        )

    def test_local_default_does_not_allow_arbitrary_hosts(self):
        self.assertEqual(self.hosts(), ["localhost", "127.0.0.1"])
