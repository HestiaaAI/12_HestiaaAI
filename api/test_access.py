"""The product catalogue and canonical CSV share the household boundary."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from households.models import Membership, Workspace
from workflows.models import Task

class ProductAccessTests(TestCase):
    def test_removed_transports_are_404_without_external_work(self):
        with patch('api.external.requests.get') as provider:
            for url in ['/api/tasks/','/api/ai/brain-dump/','/api/external/products/','/api/response-demo/']:
                self.assertEqual(self.client.get(url).status_code,404)
                self.assertEqual(self.client.post(url).status_code,404)
            provider.assert_not_called()

    def test_private_data_status_and_cache_boundaries(self):
        url='/tasks/export.csv'
        self.assertEqual(self.client.get(url).status_code,401)
        user=get_user_model().objects.create_user('csv-reader')
        self.client.force_login(user)
        response=self.client.get(url)
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json(),{'error':'Select a household to continue.','code':'household_required'})
        home=Workspace.objects.create(name='CSV household')
        member=Membership.objects.create(user=user,workspace=home,display_name='Reader')
        Task.objects.create(workspace=home,title='Visible CSV task')
        response=self.client.get(url)
        self.assertContains(response,'Visible CSV task')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertIn('Cookie',response['Vary'])
        Membership.objects.filter(pk=member.pk).update(is_active=False)
        self.assertEqual(self.client.get(url).status_code,409)

    def test_unauthorized_catalogue_never_calls_upstream(self):
        with patch('api.external.requests.get') as provider:
            self.assertEqual(self.client.get('/lookup/?q=milk').status_code,302)
            self.client.force_login(get_user_model().objects.create_user('outsider'))
            self.assertEqual(self.client.get('/lookup/?q=milk').status_code,302)
            provider.assert_not_called()
