from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение, предоставляющее доступ на чтение всем пользователям,
    а на изменение и удаление — только автору объекта.
    """

    def has_object_permission(self, request, view, obj):
        """
        Проверяет права доступа к конкретному объекту.

        Разрешает:
        - безопасные методы (GET, HEAD, OPTIONS) всем
        - небезопасные методы (POST, PUT, DELETE и т.д.) только автору
        Args:
            request (HttpRequest): объект запроса
            view (View): текущая view
            obj (Model): объект, к которому запрашивается доступ

        Returns:
            bool: True — доступ разрешён, False — запрещён
        """
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
