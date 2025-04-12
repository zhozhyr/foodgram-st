import django_filters

from recipes.models import Recipe
from django_filters.rest_framework import BooleanFilter


class RecipeFilter(django_filters.FilterSet):
    """
    Фильтр для рецептов по полям:
    - is_favorited: возвращает рецепты, добавленные в избранное текущим пользователем
    - is_in_shopping_cart: возвращает рецепты, добавленные в корзину текущим пользователем
    - author: фильтрация по автору рецепта
    """
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author']

    def filter_is_favorited(self, queryset, name, value):
        """
        Фильтрует рецепты, добавленные в избранное текущим пользователем.

        Args:
            queryset (QuerySet): исходный набор рецептов
            name (str): имя фильтра (is_favorited)
            value (bool): значение фильтра из запроса

        Returns:
            QuerySet: отфильтрованные рецепты
        """
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Фильтрует рецепты, добавленные в корзину текущим пользователем.

        Args:
            queryset (QuerySet): исходный набор рецептов
            name (str): имя фильтра (is_in_shopping_cart)
            value (bool): значение фильтра из запроса

        Returns:
            QuerySet: отфильтрованные рецепты
        """
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset
