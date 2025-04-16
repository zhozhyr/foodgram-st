from rest_framework.pagination import PageNumberPagination

from foodgram.constants import MAX_PAGE_SIZE


class Pagination(PageNumberPagination):
    """
    Кастомный пагинатор с поддержкой параметров `limit` и `page`.

    Параметры запроса:
    - `limit`: количество объектов на странице (по умолчанию `page_size`)
    - `page`: номер страницы
    - `MAX_PAGE_SIZE`: максимальное число объектов на странице
    """

    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE
    page_query_param = 'page'
