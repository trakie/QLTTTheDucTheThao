from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Class, Enrollment, Membership, Trainer, Schedule

admin.site.register(UserProfile, UserAdmin)
admin.site.register(Class)
admin.site.register(Enrollment)
admin.site.register(Membership)
admin.site.register(Trainer)
admin.site.register(Schedule)

# Register your models here.
