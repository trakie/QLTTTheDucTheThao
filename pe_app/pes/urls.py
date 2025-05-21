from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('enroll/', views.enroll, name='enroll'),
    path("accounts/", include("django.contrib.auth.urls")),
]
