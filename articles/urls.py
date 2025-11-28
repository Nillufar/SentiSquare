from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('overview/', views.overview, name='overview'),
    path('article/<int:article_id>/', views.article_detail, name='article_detail'),
    path('article/<int:article_id>/level/<int:level>/', views.get_article_level, name='get_article_level'),
    path('article/<int:article_id>/process/', views.process_article, name='process_article'),
    path('article/<int:article_id>/generate-level/', views.generate_article_level, name='generate_article_level'),
    path('import/', views.import_article, name='import_article'),
]
