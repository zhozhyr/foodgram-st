from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class Pagination(PageNumberPagination):
    """
    Кастомный пагинатор с поддержкой параметров `limit` и `page`.

    Параметры запроса:
    - `limit`: количество объектов на странице (по умолчанию `page_size`)
    - `page`: номер страницы

    Максимальное количество элементов на странице — 100.
    """
    page_size_query_param = 'limit'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Формирует структуру ответа для пагинированного списка.

        Args:
            data (list): Сериализованные объекты текущей страницы

        Returns:
            Response: словарь с ключами `count`, `next`, `previous`, `results`
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
