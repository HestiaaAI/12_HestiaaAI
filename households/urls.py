from django.urls import path
from . import views, invitation_views, invitation_acceptance, management_views, energy_views
app_name = 'households'
urlpatterns = [
    path('current/members/<int:membership_id>/remove/', management_views.remove, name='remove-member'),
    path('current/members/<int:membership_id>/transfer/', management_views.transfer, name='transfer-owner'),
    path('current/leave/', management_views.leave, name='leave'),
    path('current/energy/<int:workspace_id>/', energy_views.planner, name='energy'),
    path('current/', management_views.detail, name='detail'),
    path('current/settings/', management_views.settings, name='settings'),
    path("invites/<str:token>/", invitation_acceptance.accept, name="accept-invite"),
    path("current/invites/", invitation_views.invites, name="invites"),
    path("current/invites/<int:invitation_id>/revoke/", invitation_views.revoke, name="revoke-invite"),
    path("current/invites/<int:invitation_id>/resend/", invitation_views.resend, name="resend-invite"),
    path("create/", views.create, name="create"),
    path('', views.household_list, name='list'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('switch/', views.switch, name='switch'),
]
