from django.urls import path

from . import views

urlpatterns = [
    path('', views.LogSearchView.as_view(), name='log_search'),
]
