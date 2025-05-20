from django.contrib import admin
from .models import UserProfile, Class, Enrollment,Membership, Trainer

admin.site.register(UserProfile)
admin.site.register(Class)
admin.site.register(Enrollment)
admin.site.register(Membership)
admin.site.register(Trainer)

# Register your models here.
