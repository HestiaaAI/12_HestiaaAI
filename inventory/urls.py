from django.urls import path

from inventory import views

app_name = "groceries"

urlpatterns = [
    path("", views.groceries, name="list"),
    path("household/", views.household, name="household"),
    path("<int:workspace_id>/", views.groceries, name="workspace"),
    path("<int:workspace_id>/scan/", views.scan_receipt, name="scan"),
    path("<int:workspace_id>/add/", views.edit_batch, name="add"),
    path("<int:workspace_id>/<int:batch_id>/edit/", views.edit_batch, name="edit"),
    path("<int:workspace_id>/<int:batch_id>/close/", views.close_batch, name="close"),
    path("<int:workspace_id>/suggest/", views.suggest, name="suggest"),
    path("<int:workspace_id>/approve/", views.approve, name="approve"),
]
