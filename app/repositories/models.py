"""
Models for repositories app.
"""
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

name_validator = RegexValidator(
    regex=r'^[a-z0-9]+(-[a-z0-9]+)*$',
    message='Name must be lowercase alphanumeric characters and hyphens, no spaces.',
)


class Repository(models.Model):
    """A Docker image repository, owned by a user or marked official."""

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='repositories',
    )
    name = models.CharField(max_length=100, validators=[name_validator])
    short_description = models.CharField(max_length=255, blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    is_official = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_owner_repository_name'),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        if self.is_official:
            return self.name
        return f'{self.owner.username}/{self.name}'
