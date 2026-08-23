from django.urls import path

from . import views

urlpatterns = [
    path('', views.ExploreListView.as_view(), name='explore'),
]
