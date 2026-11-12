from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


TEMPERATURE_VALIDATORS = [MinValueValidator(55), MaxValueValidator(85)]


class Workspace(models.Model):
    """
    Represents one household or team using Hestia.

    It exists as the main container for members, documents,
    inventory records, tasks, and other Hestia data.
    """

    class WorkspaceType(models.TextChoices):
        HOUSEHOLD = "HOUSEHOLD", "Household"
        TEAM = "TEAM", "Team"

    workspace_id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=120)
    workspace_type = models.CharField(
        max_length=30,
        choices=WorkspaceType.choices,
        default=WorkspaceType.HOUSEHOLD,
    )
    timezone = models.CharField(
        max_length=50,
        default="America/Chicago",
    )

    weather_location = models.CharField(max_length=80, blank=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="hestia_workspaces",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    """
    Represents a person's membership in a Hestia workspace.

    It connects a Django user to a workspace and stores the
    member's display name, household role, permissions, and status.
    """

    class MemberRole(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADULT = "ADULT", "Roommate"
        CHILD = "CHILD", "Child"
        CAREGIVER = "CAREGIVER", "Caregiver"
        LIMITED = "LIMITED", "Limited"
        OTHER = "OTHER", "Other"

    membership_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hestia_memberships",
    )

    display_name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=30,
        choices=MemberRole.choices,
        default=MemberRole.ADULT,
    )

    can_manage_sources = models.BooleanField(default=False)
    can_assign_tasks = models.BooleanField(default=False)
    can_receive_assignments = models.BooleanField(default=True)

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["workspace__name", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_user_membership_per_workspace",
            )
        ]

    def __str__(self):
        return f"{self.display_name} - {self.workspace.name}"

class HouseholdInvitation(models.Model):
    """Digest-only, email-bound grant; raw tokens are never persisted."""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField(max_length=254)
    token_digest = models.CharField(max_length=64, unique=True)
    request_digest = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    invited_by = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, related_name='issued_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_household_invitations')
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['workspace', 'email'], name='household_invite_email_idx')]

    @property
    def status(self):
        from django.utils import timezone
        if self.revoked_at:
            return 'revoked'
        if self.accepted_at:
            return 'accepted'
        return 'expired' if self.expires_at <= timezone.now() else 'pending'

    def __str__(self):
        return f'Household invitation {self.pk}'


class ThermostatPreference(models.Model):
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE)
    day_min = models.PositiveSmallIntegerField(validators=TEMPERATURE_VALIDATORS)
    day_max = models.PositiveSmallIntegerField(validators=TEMPERATURE_VALIDATORS)
    night_min = models.PositiveSmallIntegerField(validators=TEMPERATURE_VALIDATORS)
    night_max = models.PositiveSmallIntegerField(validators=TEMPERATURE_VALIDATORS)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(day_min__lte=models.F("day_max")),
                name="thermostat_day_range_order",
            ),
            models.CheckConstraint(
                condition=models.Q(night_min__lte=models.F("night_max")),
                name="thermostat_night_range_order",
            ),
        ]
