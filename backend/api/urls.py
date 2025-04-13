from django.urls import include, path
from rest_framework import routers

import api.views as views

# Основные роутеры
user_router = routers.DefaultRouter()
recipe_router = routers.DefaultRouter()

user_router.register('users', views.UserViewSet, basename='users')
recipe_router.register('recipes', views.RecipeViewSet, basename='recipes')
recipe_router.register('ingredients', views.IngredientViewSet,
                       basename='ingredients')

urlpatterns = [
    # API маршруты
    path('', include(user_router.urls)),
    path('', include(recipe_router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
