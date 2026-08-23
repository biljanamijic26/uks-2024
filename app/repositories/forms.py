"""
Forms for repositories app.
"""
from django import forms

from .models import Repository, Tag


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


class TagCreateForm(forms.ModelForm):
    """Form for creating a new tag."""

    class Meta:
        model = Tag
        fields = ('name', 'digest', 'size')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'latest'}),
            'digest': forms.TextInput(attrs={'placeholder': 'sha256:' + 'a' * 64}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    def clean_name(self):
        name = self.cleaned_data['name']
        if Tag.objects.filter(repository=self.instance.repository, name=name).exists():
            raise forms.ValidationError('A tag with this name already exists in this repository.')
        return name


class TagEditForm(forms.ModelForm):
    """Form for editing an existing tag. Name is not editable."""

    class Meta:
        model = Tag
        fields = ('digest', 'size')
        widgets = {
            'digest': forms.TextInput(attrs={'placeholder': 'sha256:' + 'a' * 64}),
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
