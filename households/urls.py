from django.urls import path
from . import views, invitation_views, invitation_acceptance
app_name = 'households'
urlpatterns = [
    path("invites/<str:token>/", invitation_acceptance.accept, name="accept-invite"),
    path("current/invites/", invitation_views.invites, name="invites"),
    path("current/invites/<int:invitation_id>/revoke/", invitation_views.revoke, name="revoke-invite"),
    path("current/invites/<int:invitation_id>/resend/", invitation_views.resend, name="resend-invite"),
    path("create/", views.create, name="create"),
    path('', views.household_list, name='list'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('switch/', views.switch, name='switch'),
]
