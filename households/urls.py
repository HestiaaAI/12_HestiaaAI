from django.urls import path
from . import views
app_name = 'households'
urlpatterns = [
    path('', views.household_list, name='list'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('switch/', views.switch, name='switch'),
]
