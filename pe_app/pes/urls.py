from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('enroll/<int:pk>/', views.enroll, name='enroll'),
    path("accounts/", include("django.contrib.auth.urls")),
    path('class/<int:pk>/', views.class_detail, name='class_detail'),
    path('trainer/<int:pk>/', views.trainer_detail, name='trainer_detail')
]
