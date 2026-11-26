from django.urls import path
from . import views

urlpatterns = [
    path('', views.forum, name='forum'),
    path('search/', views.searchView, name='search-result'),
    path('create-topic/', views.userPost, name='user-post'),
    path('topic/<int:pk>/', views.postTopic, name='topic-detail'),
    path('topic/<int:pk>/edit/', views.editPost, name='edit-post'),
    path('topic/<int:pk>/load-answers/', views.load_more_answers, name='load-more-answers'),
    path('answer/<int:answer_pk>/edit/', views.edit_answer, name='edit-answer'),
    path('answer/<int:answer_pk>/delete/', views.delete_answer, name='delete-answer'),
    path('upvote/', views.upvote, name='upvote'),
    path('downvote/', views.downvote, name='downvote'),
    path('categories/', views.category_list, name='category-list'),
    path('category/<int:category_id>/', views.categoryDetailView, name='category-detail'),
    path('blog/', views.blogListView, name='blog-listing'),
    path('blog/<slug:slug>/', views.blogDetailView, name='article-detail'),
    path('dashboard/', views.userDashboard, name='user-dashboard'),
]