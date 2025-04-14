from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from recipes.models import Recipe


def manage_user_recipe(request, pk, model, serializer_class):
    """
    Обработчик для добавления и удаления рецептов
    из пользовательских коллекций (например, избранного или корзины).

    Поддерживает методы:
    - POST: добавление рецепта в коллекцию;
    - DELETE: удаление рецепта из коллекции.

    Аргументы:
        request (HttpRequest): объект запроса DRF.
        pk (int): первичный ключ рецепта.
        model (Model): модель, представляющая коллекцию
        serializer_class (Serializer): сериализатор, связанный с моделью.

    Возвращает:
        Response: объект DRF Response с соответствующим статусом и данными.

    Возможные ответы:
        - 201 Created: успешное добавление;
        - 204 No Content: успешное удаление;
        - 400 Bad Request: попытка удалить несуществующую запись.
        - 404 Not Found: рецепт не найден.
    """
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == 'POST':
        serializer = serializer_class(data={
            'user': request.user.id,
            'recipe': recipe.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    deleted_count, _ = model.objects.filter(
        user=request.user, recipe=recipe
    ).delete()

    if deleted_count == 0:
        return Response(
            {"detail": f"Рецепт не найден в {model._meta.verbose_name}."},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(status=status.HTTP_204_NO_CONTENT)
