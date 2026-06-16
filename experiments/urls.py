from django.urls import path

from . import views


app_name = "experiments"

urlpatterns = [
    path("", views.experiment_list, name="experiment_list"),
    path("new/", views.experiment_create, name="experiment_create"),
    path("<int:pk>/", views.experiment_detail, name="experiment_detail"),
    path("<int:pk>/responses/export/", views.export_responses_csv, name="export_responses_csv"),
    path(
        "<int:pk>/responses/<int:response_id>/delete/",
        views.delete_experiment_response,
        name="delete_experiment_response",
    ),
]
