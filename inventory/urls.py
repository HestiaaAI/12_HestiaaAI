from django.urls import path

from inventory import views
from expenses import purchase_views

app_name = "groceries"

urlpatterns = [
    path("<int:workspace_id>/shopping/",purchase_views.purchase_list,name="shopping"),
    path("<int:workspace_id>/shopping/<int:item_id>/join/",purchase_views.join_purchase,name="shopping-join"),
    path("<int:workspace_id>/shopping/<int:item_id>/check/",purchase_views.check_purchase,name="shopping-check"),
    path("<int:workspace_id>/receipts/",purchase_views.receipt_upload,name="receipt-split"),
    path("<int:workspace_id>/receipts/<int:draft_id>/",purchase_views.receipt_review,name="receipt-split-review"),
    path("", views.groceries, name="list"),
    path("household/", views.household, name="household"),
    path("household/<int:workspace_id>/energy/", views.household_energy, name="energy"),
    path("<int:workspace_id>/", views.groceries, name="workspace"),
    path("<int:workspace_id>/scan/", views.scan_receipt, name="scan"),
    path("<int:workspace_id>/add/", views.edit_batch, name="add"),
    path("<int:workspace_id>/<int:batch_id>/edit/", views.edit_batch, name="edit"),
    path("<int:workspace_id>/<int:batch_id>/close/", views.close_batch, name="close"),
    path("<int:workspace_id>/suggest/", views.suggest, name="suggest"),
    path("<int:workspace_id>/approve/", views.approve, name="approve"),
]
