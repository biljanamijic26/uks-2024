from django.contrib import admin
from django.urls import path, include
from repositories.registry_views import registry_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('accounts.urls')),
    path('repositories/', include('repositories.urls')),
    path('explore/', include('explore.urls')),
    path('registry/token/', registry_token, name='registry_token'),
]
