"""Removed assignment surfaces must be absent, not redirected or exempted."""
from django.test import SimpleTestCase
from django.urls import resolve, reverse, Resolver404

REMOVED_ROUTES = (
    '/tasks/manual/', '/tasks/render/', '/tasks/cbv-base/', '/tasks/cbv-generic/',
    '/tasks/search/', '/tasks/search/post/', '/api/response-demo/', '/vega-lite/',
    '/vega-lite/chart1.json', '/vega-lite/chart1.png', '/vega-lite/chart2.json', '/vega-lite/chart2.png',
    '/api/charts/task-priorities/', '/api/charts/task-creations/', '/reports/tasks/', '/analytics/tasks/',
    '/reports/tasks/export.csv', '/reports/tasks/export.json', '/api/tasks/',
    '/api/external/products/', '/api/ai/brain-dump/', '/api/tasks/1/action-plan/',
)

class ProductRouteTests(SimpleTestCase):
    def test_assignment_routes_do_not_resolve(self):
        for url in REMOVED_ROUTES:
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url)

    def test_product_routes_still_resolve(self):
        for name,kwargs in [('task_forms:board',{}),('workflows:task-insights',{}),
                            ('workflows:task-detail',{'pk':1}),('workflows:task-action-plan',{'pk':1}),
                            ('workflows:task-export-csv',{}),('ai_tasks:brain-dump',{}),
                            ('households:list',{}),('accounts:login',{}),('accounts:signup',{}),('product-lookup',{})]:
            self.assertEqual(resolve(reverse(name,kwargs=kwargs)).view_name,name)

    def test_priority_png_no_longer_resolves(self):
        with self.assertRaises(Resolver404):
            resolve('/analytics/tasks/priority.png')

    def test_landing_only_describes_current_product_features(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,'reports, and charts')
        self.assertContains(response,'household insights')
