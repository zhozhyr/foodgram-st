from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    """
    Кастомный пагинатор с поддержкой параметров `limit` и `page`.

    Параметры запроса:
    - `limit`: количество объектов на странице (по умолчанию `page_size`)
    - `page`: номер страницы

    Максимальное количество элементов на странице — 6.
    """

    page_size_query_param = 'limit'
    max_page_size = 6
    page_query_param = 'page'
