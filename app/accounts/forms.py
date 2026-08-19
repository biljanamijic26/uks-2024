"""
Forms for accounts app.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    """Registration form extending Django's UserCreationForm with a required email field."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
