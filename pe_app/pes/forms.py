from django import forms
from .models import Enrollment


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['schedule_selected']  # Add other fields if needed

    def __init__(self, *args, **kwargs):
        class_obj = kwargs.pop('class_obj', None)
        super().__init__(*args, **kwargs)
        if class_obj:
            self.fields['schedule_selected'].queryset = class_obj.schedules.all()