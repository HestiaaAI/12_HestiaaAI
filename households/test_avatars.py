from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import UserAvatar
from .avatars import AvatarForm, render_avatar

class AvatarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='avatar-owner', password='test-password')
        self.other = get_user_model().objects.create_user(username='avatar-other')

    def test_login_required(self):
        self.assertEqual(self.client.get(reverse('accounts:avatar')).status_code, 302)

    def test_save_only_own_avatar_and_preview(self):
        self.client.force_login(self.user)
        data = {name: field.choices[0][0] for name, field in AvatarForm().fields.items()}
        data['hair_style'] = 'curls'
        data['user'] = self.other.pk
        response = self.client.post(reverse('accounts:avatar'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserAvatar.objects.get(user=self.user).options['hair_style'], 'curls')
        self.assertFalse(UserAvatar.objects.filter(user=self.other).exists())
        self.assertContains(response, 'Your avatar is saved')

    def test_invalid_choices_cannot_be_saved_or_injected(self):
        self.client.force_login(self.user)
        data = {name: field.choices[0][0] for name, field in AvatarForm().fields.items()}
        data['skin'] = '<script>alert(1)</script>'
        self.assertEqual(self.client.post(reverse('accounts:avatar'), data).status_code, 200)
        self.assertFalse(UserAvatar.objects.exists())
        self.assertNotIn('<script', render_avatar(data))

    def test_saved_avatar_replaces_header_initials(self):
        UserAvatar.objects.create(user=self.user, options={'hair_style': 'curls'})
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/'), 'class="face-avatar"')

    def test_signup_default_opens_optional_avatar_setup(self):
        from .account_adapter import AccountAdapter
        self.assertEqual(AccountAdapter().get_signup_redirect_url(None), reverse('accounts:avatar'))

    def test_expanded_styles_and_old_profiles(self):
        from .avatars import normalized
        options = normalized({'hair_style': 'long', 'clothes': '#4f7d76'})
        self.assertEqual(options['outfit'], 'tee')
        self.assertEqual(options['face_shape'], 'oval')
        form = AvatarForm(data={**options, 'hair_style': 'braids', 'face_shape': 'heart', 'outfit': 'hoodie', 'mouth': 'grin'})
        self.assertTrue(form.is_valid(), form.errors)
        svg = render_avatar(form.cleaned_data)
        self.assertIn('data-hair="braids" style="display:inline"', svg)
        self.assertIn('data-outfit="hoodie" style="display:inline"', svg)
        self.assertIn('data-face="heart" style="display:inline"', svg)

    def test_illustrated_picker_and_detailed_features(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse('accounts:avatar'))
        self.assertContains(page, 'avatar-choice-grid')
        self.assertContains(page, 'type="radio"')
        self.assertContains(page, 'Earrings')
        svg = render_avatar({'eyes':'almond', 'accessory':'bandana', 'earrings':'hoops'})
        self.assertIn('data-accessory="bandana" style="display:inline"', svg)
        self.assertIn('data-earrings="hoops" style="display:inline"', svg)
