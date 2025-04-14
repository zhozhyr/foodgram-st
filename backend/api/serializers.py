from rest_framework import serializers
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework.exceptions import ValidationError

from foodgram.constants import (MIN_AMOUNT_VALUE, MAX_INGREDIENT_AMOUNT,
                                MIN_COOKING_TIME_VALUE, MAX_COOKING_TIME_VALUE)

from api.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeComponent,
                            ShoppingCart)
from users.models import Subscription

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    """
    Сериализатор пользователя с дополнительными полями:
    - is_subscribed: подписан ли текущий пользователь на этого
    - avatar: изображение профиля
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta(DjoserUserSerializer.Meta):
        fields = DjoserUserSerializer.Meta.fields + ('is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.subscriptions.filter(author=obj).exists())

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиента в составе рецепта.
    Используется при создании и обновлении рецептов.
    """

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT_VALUE,
        max_value=MAX_INGREDIENT_AMOUNT
    )

    class Meta:
        model = RecipeComponent
        fields = ['id', 'amount']


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор ингредиента.
    Используется при отображении состава рецепта.
    """

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления рецептов.

    Особенности:
    - Обрабатывает входящие данные по ингредиентам (write_only).
    - Валидирует время приготовления и список ингредиентов.
    - Добавляет флаги is_favorited и is_in_shopping_cart.
    - В ответе использует читающий сериализатор RecipeReadSerializer.
    """

    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, write_only=True
    )
    read_ingredients = serializers.SerializerMethodField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'text', 'image', 'cooking_time',
            'ingredients', 'read_ingredients',
            'is_favorited', 'is_in_shopping_cart'
        )

    def validate_cooking_time(self, value):
        if not MIN_COOKING_TIME_VALUE <= value <= MAX_COOKING_TIME_VALUE:
            raise ValidationError({
                "cooking_time": (
                    f"Время готовки должно быть от {MIN_COOKING_TIME_VALUE} "
                    f"до {MAX_COOKING_TIME_VALUE} минут."
                )
            })
        return value

    def validate(self, data):
        ingredients_data = data.get('ingredients')
        if not ingredients_data:
            raise ValidationError(
                {"ingredients": ["Список ингредиентов не может быть пустым."]}
            )

        ids = [item['id'] for item in ingredients_data]
        if len(ids) != len(set(ids)):
            raise ValidationError(
                {"ingredients": ["Ингредиенты не должны повторяться."]}
            )
        return data

    def create_recipe_ingredients(self, recipe, ingredients_data):
        RecipeComponent.objects.bulk_create([
            RecipeComponent(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            ) for item in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=self.context['request'].user,
                                       **validated_data)
        self.create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance.recipe_ingredients.all().delete()
        self.create_recipe_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получения рецептов (чтение).

    - Возвращает ингредиенты с количеством.
    - Показывает информацию об авторе.
    - Включает флаги is_favorited и is_in_shopping_cart,
      определяемые на основе текущего пользователя.
    """

    author = UserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'text', 'image', 'cooking_time',
            'ingredients', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_ingredients(self, obj):
        return [
            {
                **IngredientSerializer(component.ingredient).data,
                'amount': component.amount
            }
            for component in obj.recipe_ingredients.all()
        ]

    def _check_user_relation(self, obj, related_name):
        user = self.context.get('request').user
        return (user.is_authenticated
                and getattr(obj, related_name).filter(user=user).exists())

    def get_is_favorited(self, obj):
        return self._check_user_relation(obj, 'favorites')

    def get_is_in_shopping_cart(self, obj):
        return self._check_user_relation(obj, 'shopping_carts')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """
    Короткая версия рецепта.
    Используется в списках: подписки, избранное, корзина.
    """

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(UserSerializer):
    """
    Сериализатор подписок:
    - отображает рецепты автора
    - поддерживает лимит через параметр recipes_limit
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get(
            'recipes_limit') if request else None

        recipes = obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]

        return ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания подписки на автора:
    - запрещает подписку на самого себя
    - запрещает повторную подписку
    """

    class Meta:
        model = Subscription
        fields = ('author',)
        extra_kwargs = {
            'author': {'write_only': True}
        }

    def validate(self, data):
        user = self.context['request'].user
        author = data['author']

        if user == author:
            raise serializers.ValidationError(
                "Невозможно подписаться на самого себя."
            )

        if Subscription.objects.filter(follower=user, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )

        return data

    def create(self, validated_data):
        return Subscription.objects.create(
            follower=self.context['request'].user,
            **validated_data
        )

    def to_representation(self, instance):
        return FollowSerializer(instance.author, context=self.context).data


class BaseUserRecipeSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для моделей, связывающих пользователя с рецептом
    (например, избранное, корзина):
    - проверяет, что связь не дублируется
    - возвращает краткий рецепт в представлении
    """

    class Meta:
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f"Рецепт уже в {self.Meta.model._meta.verbose_name}."
            )
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(instance.recipe).data


class FavoriteSerializer(BaseUserRecipeSerializer):
    """
    Сериализатор для добавления рецепта в избранное.
    Наследуется от базового сериализатора связи user-recipe.
    """

    class Meta(BaseUserRecipeSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(BaseUserRecipeSerializer):
    """
    Сериализатор для добавления рецепта в корзину покупок.
    Наследуется от базового сериализатора связи user-recipe.
    """

    class Meta(BaseUserRecipeSerializer.Meta):
        model = ShoppingCart
