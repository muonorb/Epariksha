from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    USER_TYPES = (('teacher', 'Teacher'), ('student', 'Student'))
    user_type = forms.ChoiceField(choices=USER_TYPES)
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'user_type']
