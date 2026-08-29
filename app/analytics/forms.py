"""
Forms for analytics app.
"""
from django import forms

LOG_LEVEL_CHOICES = [
    ('', 'All levels'),
    ('DEBUG', 'Debug'),
    ('INFO', 'Info'),
    ('WARNING', 'Warning'),
    ('ERROR', 'Error'),
    ('CRITICAL', 'Critical'),
]


class LogSearchForm(forms.Form):
    """Search form for the admin log search page: text content, log level, and date range."""

    q = forms.CharField(required=False, label='Text', widget=forms.TextInput(attrs={'placeholder': 'Search message text'}))
    level = forms.ChoiceField(choices=LOG_LEVEL_CHOICES, required=False)
    date_after = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_before = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    advanced_q = forms.CharField(
        required=False, label='Advanced query',
        widget=forms.TextInput(attrs={
            'placeholder': '(level:warning OR level:error) AND message:"error occurred"',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)
