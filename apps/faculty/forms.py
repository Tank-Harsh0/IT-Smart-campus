from django import forms
from apps.assignments.models import Assignment
from apps.subjects.models import Subject
from .models import Faculty

class AssignmentCreateForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['subject', 'title', 'description', 'due_date', 'file']
        widgets = {
            'subject': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full p-2 border rounded'}),
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'w-full p-2 border rounded'}),
        }
    
    def __init__(self, *args, faculty=None, **kwargs):
        super().__init__(*args, **kwargs)
        if faculty:
            # Filter subjects to only those taught by this faculty
            self.fields['subject'].queryset = Subject.objects.filter(faculty=faculty)
class FacultyProfileForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = [
            'photo',
            'designation', 
            'qualification', 
            'dept_joining_date', 
            'institute_joining_date', 
            'area_of_interest', 
            'courses_taught', 
            'portfolio'
        ]
        widgets = {
            'designation': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700'}),
            'qualification': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700'}),
            'dept_joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700'}),
            'institute_joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700'}),
            'area_of_interest': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700 resize-none'}),
            'courses_taught': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700 resize-none'}),
            'portfolio': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 font-bold text-slate-700'}),
            'photo': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
        }