from django.urls import path

from . import views

app_name = "seekers"

urlpatterns = [
    path("me/", views.SeekerProfileView.as_view(), name="me"),
]
