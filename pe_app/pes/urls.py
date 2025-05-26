from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('enroll/<int:pk>/', views.enroll, name='enroll'),
    path('accounts/', include("django.contrib.auth.urls")),
    path('class/<int:pk>/', views.class_detail, name='class_detail'),
    path('trainer/<int:pk>/', views.trainer_detail, name='trainer_detail'),
    path('payment/<int:enrollment_id>/', views.payment, name='payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('profile/<int:pk>/', views.profile, name='profile'),
    path('trainer/get-class-members/<int:class_id>/',
         views.get_class_members,
         name='get_class_members'),
    path('trainer/update-enrollment/<int:enrollment_id>/',
         views.update_enrollment,
         name='update_enrollment'),
    path('update-avatar/', views.update_avatar, name='update_avatar'),
    path('receipts/', views.receipts, name='receipts'),
    path('class-schedule/', views.class_schedule, name='class_schedule'),
    path('news/', views.news, name='news'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
]
