import base64
import os
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from api.fields import Base62Field
from api.filters import RecipeFilter
from api.paginations import Pagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (FavoriteSerializer, FollowSerializer,
                             IngredientSerializer,
                             RecipeReadSerializer, RecipeWriteSerializer,
                             ShoppingCartSerializer, SubscriptionSerializer,
                             UserSerializer)
from api.services import manage_user_recipe
from api.utils.shopping_cart_export import (
    export_shopping_cart_txt,
    export_shopping_cart_csv,
    export_shopping_cart_pdf,
)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeComponent,
                            ShoppingCart)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """
    Вьюсет для работы с пользователями:
    - получение текущего пользователя (me)
    - управление аватаром (загрузка и удаление)
    - список подписок
    - подписка / отписка от автора
    """

    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    pagination_class = Pagination
    permission_classes = [permissions.AllowAny]

    @action(detail=False,
            methods=['get'],
            permission_classes=[permissions.IsAuthenticated]
            )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['put', 'delete'],
            permission_classes=[permissions.IsAuthenticated],
            url_path='me/avatar'
            )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')

            if not avatar_data:
                return Response(
                    {"avatar": ["Это поле обязательно."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if user.avatar:
                    user.avatar.delete()

                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr),
                                   name=f"{uuid.uuid4()}.{ext}")

                user.avatar.save(data.name, data, save=True)
                user.save()

                avatar_url = request.build_absolute_uri(user.avatar.url)

                return Response({"avatar": avatar_url},
                                status=status.HTTP_200_OK)

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if user.avatar:
            avatar_path = user.avatar.path
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
            user.avatar.delete()
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "Аватар отсутствует."},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False,
            methods=['get'],
            url_path='subscriptions',
            permission_classes=[permissions.IsAuthenticated]
            )
    @action(detail=False,
            methods=['get'],
            url_path='subscriptions',
            permission_classes=[permissions.IsAuthenticated])
    def get_subscriptions(self, request):
        authors = User.objects.filter(subscriptions__follower=request.user)

        page = self.paginate_queryset(authors)
        serializer = FollowSerializer(page, many=True,
                                      context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='subscribe',
            permission_classes=[permissions.IsAuthenticated]
            )
    def manage_subscription(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'author': author.id, 'follower': user.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            follow = serializer.save()
            return Response(
                FollowSerializer(follow.author,
                                 context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        deleted, _ = user.subscriptions.filter(author=author).delete()
        if not deleted:
            return Response(
                {"detail": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы с рецептами:
    - стандартные CRUD-операции
    - получение короткой ссылки
    - редирект по base62-коду
    - управление избранным и корзиной
    - генерация списка покупок в txt/csv/pdf
    """

    queryset = Recipe.objects.all().select_related(
        'author').prefetch_related('ingredients')
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_code = Base62Field.to_base62(recipe.id)
        short_link = request.build_absolute_uri(f"/s/{short_code}")
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    def redirect_to_recipe(self, request, short_code=None):
        try:
            recipe_id = Base62Field.from_base62(short_code)
        except ValueError:
            return Response(
                {"detail": "Неверный короткий код."},
                status=status.HTTP_400_BAD_REQUEST
            )

        recipe = get_object_or_404(Recipe, id=recipe_id)
        redirect_url = request.build_absolute_uri(f"/recipes/{recipe.id}/")
        return redirect(redirect_url)

    def get_ingredients_list_from_cart(self, user):
        return (
            RecipeComponent.objects
            .filter(recipe__shopping_carts__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum('amount'))
            .order_by('ingredient__name')
        )

    def serialize_ingredients(self, ingredients):
        return [
            {
                'name': item['ingredient__name'],
                'amount': item['amount'],
                'measurement_unit': item['ingredient__measurement_unit']
            }
            for item in ingredients
        ]

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        ingredients = self.serialize_ingredients(
            self.get_ingredients_list_from_cart(request.user)
        )
        file_format = request.query_params.get('format', 'txt').lower()

        exporters = {
            'txt': export_shopping_cart_txt,
            'csv': export_shopping_cart_csv,
            'pdf': export_shopping_cart_pdf,
        }

        if not (exporter := exporters.get(file_format)):
            return Response(
                {"detail": "Выбран неверный формат файла"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return exporter(ingredients)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_shopping_cart(self, request, pk=None):
        return manage_user_recipe(
            request,
            pk,
            ShoppingCart,
            ShoppingCartSerializer
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_favorite(self, request, pk=None):
        return manage_user_recipe(
            request,
            pk,
            Favorite,
            FavoriteSerializer
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для просмотра ингредиентов.
    Поддерживает поиск по префиксу названия (`?name=`).
    Без пагинации.
    """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (SearchFilter,)
    search_fields = ['name']
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset
