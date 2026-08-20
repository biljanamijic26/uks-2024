from django.urls import path

from . import views

urlpatterns = [
    path('', views.RepositoryListView.as_view(), name='repository_list'),
    path('new/', views.RepositoryCreateView.as_view(), name='repository_create'),
    path('<str:owner>/<str:name>/', views.RepositoryDetailView.as_view(), name='repository_detail'),
    path('<str:owner>/<str:name>/edit/', views.RepositoryUpdateView.as_view(), name='repository_edit'),
    path('<str:owner>/<str:name>/delete/', views.RepositoryDeleteView.as_view(), name='repository_delete'),
]
