from django.urls import path

from . import views

urlpatterns = [
    path('', views.RepositoryListView.as_view(), name='repository_list'),
    path('new/', views.RepositoryCreateView.as_view(), name='repository_create'),
    path('official/new/', views.OfficialRepositoryCreateView.as_view(), name='official_repository_create'),
    path('<str:owner>/<str:name>/', views.RepositoryDetailView.as_view(), name='repository_detail'),
    path('<str:owner>/<str:name>/edit/', views.RepositoryUpdateView.as_view(), name='repository_edit'),
    path('<str:owner>/<str:name>/delete/', views.RepositoryDeleteView.as_view(), name='repository_delete'),
    path('<str:owner>/<str:name>/tags/new/', views.TagCreateView.as_view(), name='tag_create'),
    path('<str:owner>/<str:name>/tags/<str:tag_name>/edit/', views.TagUpdateView.as_view(), name='tag_edit'),
    path('<str:owner>/<str:name>/tags/<str:tag_name>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
]
