from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Membership, SharingCircle, Workspace


class SharingTests(TestCase):
    def test_owner_and_removed_member_cannot_read_selected_circle(self):
        from .sharing import visible_circles

        home = Workspace.objects.create(name="Home")
        owner, creator, reader = [
            Membership.objects.create(
                workspace=home, display_name=name, role=role,
                user=get_user_model().objects.create_user(username=name),
            )
            for name, role in (("owner", "OWNER"), ("creator", "ADULT"), ("reader", "ADULT"))
        ]
        circle = SharingCircle.objects.create(
            workspace=home, created_by=creator, name="Birthday", visibility="SELECTED",
        )
        circle.selected_readers.add(reader)
        self.assertFalse(visible_circles(actor=owner).exists())
        self.assertEqual(list(visible_circles(actor=creator)), [circle])
        self.assertEqual(list(visible_circles(actor=reader)), [circle])
        Membership.objects.filter(pk=reader.pk).update(is_active=False)
        self.assertFalse(visible_circles(actor=reader).exists())
