"""
Forms for repositories app.
"""
from django import forms

from .models import Repository


def _style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.RadioSelect):
            continue
        css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        field.widget.attrs.setdefault('class', css_class)


class RepositoryCreateForm(forms.ModelForm):
    """Form for creating a new repository."""

    class Meta:
        model = Repository
        fields = ('name', 'short_description', 'visibility')
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 3}),
            'visibility': forms.RadioSelect(attrs={'class': 'form-check-input mt-1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class RepositoryEditForm(forms.ModelForm):
    """Form for editing an existing repository. Name is not editable."""

    class Meta:
        model = Repository
        fields = ('short_description', 'visibility')
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 3}),
            'visibility': forms.RadioSelect(attrs={'class': 'form-check-input mt-1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
