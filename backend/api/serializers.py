from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework.exceptions import ValidationError

from api.fields import Base64ImageField
from foodgram.constants import MIN_COOKING_TIME_VALUE
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
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(follower=user, author=obj).exists()

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиента в составе рецепта.
    Используется при создании и обновлении рецептов.
    """
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1)

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


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор рецепта:
    - чтение: возвращает данные вместе с автором, ингредиентами,
      статусом в избранном и корзине
    - запись: принимает ingredients_data, обрабатывает загрузку изображения в base64
    """
    # поля для чтения
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField(read_only=True)

    # поле для записи
    ingredients_data = RecipeIngredientSerializer(
        many=True, write_only=True, source='ingredients'
    )

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'ingredients_data',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.shopping_carts.filter(user=user).exists()

    def get_ingredients(self, obj):
        ingredients = []
        for recipe_ingredient in obj.recipe_ingredients.all():
            ingredient_data = IngredientSerializer(recipe_ingredient.ingredient).data
            ingredient_data['amount'] = recipe_ingredient.amount
            ingredients.append(ingredient_data)
        return ingredients

    def validate_cooking_time(self, value):
        if value < MIN_COOKING_TIME_VALUE:
            raise ValidationError(
                {
                    "cooking_time": [
                        "Время готовки не может быть "
                        f"меньше {MIN_COOKING_TIME_VALUE} мин."
                    ]
                }
            )
        return value

    def validate(self, data):
        ingredients_data = data.get('ingredients', [])
        if not ingredients_data:
            raise ValidationError(
                {"ingredients": ["Список ингредиентов не может быть пустым."]}
            )

        ingredient_ids = [item['id'] for item in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {"ingredients": ["Ингредиенты не должны повторяться."]}
            )
        return data

    def create_recipe_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = [
            RecipeComponent(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeComponent.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        user = self.context['request'].user
        recipe = Recipe.objects.create(author=user, **validated_data)
        self.create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.create_recipe_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('ingredients_data', None)
        return representation


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


class SubscriptionSerializer(serializers.Serializer):
    """
    Сериализатор для создания подписки на автора:
    - проверяет, что пользователь не подписывается на самого себя
    - проверяет, что подписка не дублируется
    """
    author_id = serializers.IntegerField()

    def validate_author_id(self, value):
        user = self.context['request'].user
        author_user = get_object_or_404(User, pk=value)

        if author_user == user:
            raise serializers.ValidationError("Невозможно подписаться на себя")

        if Subscription.objects.filter(user=user, author=author_user).exists():
            raise serializers.ValidationError("Вы уже подписаны на этого пользователя")

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        author_user = User.objects.get(pk=validated_data['author_id'])

        follow = Subscription.objects.create(user=user, following=author_user)
        return follow

    def to_representation(self, instance):
        return FollowSerializer(instance.following, context=self.context).data


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
