"""
Forms for accounts app.
"""
import secrets
import string

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import User

GENERATED_PASSWORD_LENGTH = 16


def _generate_password(length=GENERATED_PASSWORD_LENGTH):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class LoginForm(AuthenticationForm):
    """Login form with Bootstrap-styled widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class StyledPasswordChangeForm(PasswordChangeForm):
    """Password change form with Bootstrap-styled widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class ProfileEditForm(forms.ModelForm):
    """Allows a user to edit their own email address. Username is not editable here."""

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class CreateAdminForm(forms.Form):
    """Lets a super admin create a new admin account. Leaving the password blank
    generates a random one, which is shown to the super admin after creation."""

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text='Leave blank to generate a random password.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def save(self):
        """Creates the admin user, returning (user, password, was_generated)."""
        password = self.cleaned_data['password']
        was_generated = not password
        if was_generated:
            password = _generate_password()

        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=password,
            role=User.Role.ADMIN,
            must_change_password=True,
        )
        return user, password, was_generated


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
