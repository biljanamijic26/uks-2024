from django.contrib import admin

from .models import Repository, Tag

admin.site.register(Repository)
admin.site.register(Tag)
