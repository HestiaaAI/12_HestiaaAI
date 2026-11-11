from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from households.models import Workspace,Membership
from expenses.purchases import create_item,join_item

class AllHouseholdShoppingTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Home')
        self.a,self.b,self.c=[Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username=name),display_name=name) for name in ['A','B','C']]
        self.client.force_login(self.a.user)
    def rows(self,view='all'):
        return self.client.get(reverse('groceries:shopping',args=[self.home.pk]),{'view':view}).context['rows']
    def test_third_roommate_moves_group_item_into_shared_household_note(self):
        item=create_item(self.a,'Vaseline',1,'personal')
        join_item(self.b,item.pk,'shared')
        self.assertEqual(self.rows()[0]['bucket'],'shared')
        join_item(self.c,item.pk,'shared')
        self.assertEqual(self.rows()[0]['bucket'],'household')
        self.assertEqual(len(self.rows('household')),1)
        self.assertEqual(len(self.rows('shared')),0)
        self.assertEqual(item.claims.count(),3)
    def test_own_units_remain_intact_when_everyone_participates(self):
        item=create_item(self.a,'Milk',1,'personal')
        join_item(self.b,item.pk,'own',2);join_item(self.c,item.pk,'shared')
        self.assertEqual(self.rows()[0]['bucket'],'household')
        self.assertEqual(item.total_units,3)
        self.assertEqual(item.claims.get(member=self.b).quantity,2)
