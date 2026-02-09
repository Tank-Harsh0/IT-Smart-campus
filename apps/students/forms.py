from django import forms
from apps.attendance.models import FaceData

class FaceRegistrationForm(forms.ModelForm):
    class Meta:
        model = FaceData
        fields = ['face_image']
        widgets = {
            'face_image': forms.FileInput(attrs={'class': 'w-full p-2 border rounded bg-white'})
        }