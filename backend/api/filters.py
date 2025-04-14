import django_filters
from django_filters.rest_framework import BooleanFilter

from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    """
    Фильтр для рецептов.

    Позволяет фильтровать рецепты по:
    - is_favorited: возвращает рецепты, добавленные в избранное
    текущим пользователем;
    - is_in_shopping_cart: рецепты, добавленные в корзину;
    - author: фильтрация по автору рецепта.
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
            queryset (QuerySet): Исходный набор рецептов.
            name (str): Имя фильтра ("is_favorited").
            value (bool): Значение фильтра из запроса.

        Returns:
            QuerySet: Отфильтрованный набор рецептов.
        """
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Фильтрует рецепты, добавленные в корзину текущим пользователем.

        Args:
            queryset (QuerySet): Исходный набор рецептов.
            name (str): Имя фильтра ("is_in_shopping_cart").
            value (bool): Значение фильтра из запроса.

        Returns:
            QuerySet: Отфильтрованный набор рецептов.
        """
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset
