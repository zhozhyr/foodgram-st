import base64
import csv
import os
import uuid
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from fpdf import FPDF
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
                             RecipeSerializer,
                             ShoppingCartSerializer,
                             SubscriptionSerializer, UserSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeComponent,
                            ShoppingCart)
from users.models import Subscription

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
    def get_subscriptions(self, request):
        user = request.user

        subscriptions = User.objects.filter(author__user=user)

        page = self.paginate_queryset(subscriptions)

        serializer = FollowSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='subscribe',
            permission_classes=[permissions.IsAuthenticated]
            )
    def manage_subscription(self, request, id=None):
        user = request.user

        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'author_id': id},
                context={'request': request}
            )

            serializer.is_valid(raise_exception=True)
            follow = serializer.save()
            return Response(
                FollowSerializer(
                    follow.following,
                    context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        author_user = get_object_or_404(User, pk=id)

        follow_instance = Subscription.objects.filter(
            user=user, author=author_user).first()

        if not follow_instance:
            return Response(
                {"detail": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow_instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def manage_user_recipe(request, pk, model, serializer_class):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == 'POST':
        serializer = serializer_class(data={
            'user': request.user.id,
            'recipe': recipe.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    item = model.objects.filter(
        user=request.user, recipe=recipe
    ).first()
    if not item:
        return Response(
            {"detail": f"Рецепт не найден в {model._meta.verbose_name}."},
            status=status.HTTP_400_BAD_REQUEST
        )
    item.delete()
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
    serializer_class = RecipeSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

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
        ingredients = (
            RecipeComponent.objects
            .filter(recipe__shopping_carts__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        return [
            {
                'name': ingredient['ingredient__name'],
                'amount': ingredient['amount'],
                'measurement_unit': ingredient['ingredient__measurement_unit']
            }
            for ingredient in ingredients
        ]

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        ingredients_list = self.get_ingredients_list_from_cart(request.user)
        file_format = request.query_params.get('format', 'txt').lower()

        format_functions = {
            'txt': self.generate_txt_file,
            'csv': self.generate_csv_file,
            'pdf': self.generate_pdf_file
        }

        generate_function = format_functions.get(file_format)

        if generate_function:
            return generate_function(ingredients_list)

        return Response(
            {"detail": "Выбран неверный формат файла"},
            status=status.HTTP_400_BAD_REQUEST
        )

    def generate_txt_file(self, ingredients):
        content = "\n".join(
            f"{i['name']} ({i['measurement_unit']}) — {i['amount']}"
            for i in ingredients
        )
        response = HttpResponse(content, content_type="text/plain")
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        return response

    def generate_csv_file(self, ingredients):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])
        for i in ingredients:
            writer.writerow([i['name'], i['amount'], i['measurement_unit']])
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.csv"'
        return response

    def generate_pdf_file(self, ingredients):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Список покупок", ln=True, align='C')

        for i in ingredients:
            pdf.cell(
                200,
                10,
                txt=f"{i['name']} ({i['measurement_unit']}) — {i['amount']}",
                ln=True
            )

        response = HttpResponse(pdf.output(dest='S').encode('latin1'), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.pdf"'
        return response

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
