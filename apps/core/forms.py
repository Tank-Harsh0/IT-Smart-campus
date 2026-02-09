from django import forms
from .models import TimetableSlot, Classroom, Batch
from apps.subjects.models import Subject
from apps.faculty.models import Faculty

# ==========================================
# 1. MANUAL BATCH FORM (Fixes your ImportError)
# ==========================================
class ManualBatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['classroom', 'name']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl', 'placeholder': 'e.g. IT611'}),
        }

# ==========================================
# 2. MANUAL TIMETABLE FORM
# ==========================================
class ManualTimetableForm(forms.ModelForm):
    
    semester = forms.IntegerField(
        min_value=1, max_value=8, initial=1, 
        widget=forms.NumberInput(attrs={'class': 'w-full p-3 border rounded-xl'})
    )
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(), 
        widget=forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'})
    )
    
    TYPE_CHOICES = [('LECTURE', 'Lecture (Whole Class)'), ('LAB', 'Lab (Specific Batch)')]
    slot_type = forms.ChoiceField(
        choices=TYPE_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'hidden'})
    )
    
    specific_batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(), 
        required=False, 
        label="Batch",
        widget=forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'})
    )

    class Meta:
        model = TimetableSlot
        fields = ['day', 'start_time', 'end_time', 'subject', 'faculty', 'room_number']
        
        widgets = {
            'day': forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full p-3 border rounded-xl'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full p-3 border rounded-xl'}),
            'subject': forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'faculty': forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'room_number': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        slot_type = cleaned_data.get('slot_type')
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        specific_batch = cleaned_data.get('specific_batch')

        # Logic 1: Time Validation
        if start and end and start >= end:
            self.add_error('end_time', 'End time must be after start time.')

        # Logic 2: Lab Batch Validation
        if slot_type == 'LAB' and not specific_batch:
            self.add_error('specific_batch', 'For Labs, you MUST select a Batch.')

        return cleaned_data