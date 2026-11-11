"""Reproducible request measurements using synthetic data and Django's client."""
import json
import os
import platform
from statistics import median
from time import perf_counter

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Membership, Workspace
from workflows.models import Task


class PageMeasurementTests(TestCase):
    def test_page_measurements(self):
        measurements = []
        for task_count in (10, 1000):
            for membership_count in (1, 20):
                user = get_user_model().objects.create_user(f'bench-{task_count}-{membership_count}')
                homes = [Workspace.objects.create(name=f'Bench {task_count}-{membership_count}-{i:02}') for i in range(membership_count)]
                Membership.objects.bulk_create([Membership(user=user, workspace=home, display_name='Reader') for home in homes])
                Task.objects.bulk_create([Task(workspace=homes[0], title=f'Task {i}', priority='HIGH') for i in range(task_count)])
                self.client.force_login(user)
                session = self.client.session
                session['active_workspace_id'] = homes[0].pk
                session.save()
                for name in ('task_forms:board', 'households:list', 'workflows:task-insights'):
                    runs, queries = [], []
                    for index in range(8):
                        with CaptureQueriesContext(connection) as captured:
                            start = perf_counter()
                            response = self.client.get(reverse(name))
                            elapsed = (perf_counter() - start) * 1000
                        self.assertEqual(response.status_code, 200)
                        if name == 'task_forms:board':
                            self.assertEqual(len(response.context['tasks']), 6)
                        runs.append(elapsed)
                        queries.append(len(captured))
                        # Board annotates occurrences/assignments and loads roommate assignees.
                        expected = {"task_forms:board":8, "households:list":3, "workflows:task-insights":5}
                        self.assertEqual(len(captured), expected[name], (name,task_count,membership_count))
                    measurements.append({'page':name, 'tasks':task_count, 'memberships':membership_count,
                                         'first_ms':round(runs[0],3), 'warm_median_ms':round(median(runs[1:]),3),
                                         'queries':queries})
        record = {'python':platform.python_version(), 'platform':platform.platform(), 'database':'SQLite in-memory',
                  'warm_samples':7, 'measurements':measurements}
        if destination := os.environ.get('HESTIA_PERFORMANCE_OUTPUT'):
            from pathlib import Path
            Path(destination).write_text(json.dumps(record, indent=2)+'\n')
        print('PAGE_MEASUREMENTS '+json.dumps(record))

class ContextWorkTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('request-reuse')
        self.home=Workspace.objects.create(name='Request snapshot')
        self.member=Membership.objects.create(user=self.user,workspace=self.home,display_name='Reader')
        self.client.force_login(self.user)

    def test_resolver_reuses_snapshot_within_one_request(self):
        from django.test import RequestFactory
        from .context import resolve_active_membership, require_household
        from .context_processors import household_context
        request=RequestFactory().get('/')
        request.user=self.user
        request.session={}
        with self.assertNumQueries(1):
            first=resolve_active_membership(request)
            self.assertIs(require_household(request),first)
            self.assertIs(resolve_active_membership(request),first)
            self.assertEqual(household_context(request)['active_membership'],first)

    def test_write_revalidates_actor_after_snapshot(self):
        from unittest.mock import patch
        from workflows.task_forms import TaskCreateForm
        original=TaskCreateForm.is_valid
        def revoke(form):
            valid=original(form)
            Membership.objects.filter(pk=self.member.pk).update(is_active=False)
            return valid
        with patch.object(TaskCreateForm,'is_valid',revoke):
            response=self.client.post(reverse('task_forms:board'),{'workspace':self.home.pk,'title':'Must not save','priority':'LOW','task_type':'CHORE'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Task.objects.filter(title='Must not save').exists())
        self.assertEqual(self.client.get(reverse('workflows:task-export-csv')).status_code,409)

    def test_membership_query_occurs_once_on_normal_pages(self):
        for name in ['task_forms:board','households:list','workflows:task-insights']:
            with CaptureQueriesContext(connection) as queries:
                response=self.client.get(reverse(name))
            self.assertEqual(response.status_code,200)
            membership_reads=[q for q in queries if 'FROM "households_membership"' in q['sql']]
            # Board also loads active roommate assignees for the create form.
            expected = 2 if name == 'task_forms:board' else 1
            self.assertEqual(len(membership_reads), expected, name)

    def test_insights_uses_accessible_text_without_image_request(self):
        Task.objects.create(workspace=self.home,title='A real task',priority='HIGH')
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertContains(response,'High: 1')
        self.assertNotContains(response,'priority.png')
        self.assertContains(response,'Download CSV')
