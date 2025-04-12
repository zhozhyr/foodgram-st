import base64

import rest_framework.serializers as slz
from django.core.files.base import ContentFile

from foodgram.constants import BASE62_ALPHABET, BASE62_DIVIDER


class Base64ImageField(slz.ImageField):
    """
    Кастомное поле для сериализации изображений в формате base64.

    Позволяет принимать изображения в формате base64 в запросах API
    и преобразовывать их в `ContentFile` для сохранения в ImageField.

    Пример строки:
    data:image/png;base64,iVBORw0KGgoAAAANS...
    """

    def to_internal_value(self, data):
        """
        Преобразует base64-строку изображения в файл, пригодный для ImageField.

        Args:
            data (str | InMemoryUploadedFile): base64-строка или файл

        Returns:
            File: Объект ContentFile для сохранения
        """
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class Base62Field:
    """
    Утилитарный класс для кодирования и декодирования чисел в base62.

    Используется для генерации коротких ссылок, основанных на ID.
    """

    def to_base62(num):
        """
        Кодирует целое число в base62-строку.

        Args:
            num (int): Число для кодирования

        Returns:
            str: Строка в base62
        """
        if num == 0:
            return BASE62_ALPHABET[0]

        base62 = []
        while num:
            base62.append(BASE62_ALPHABET[num % BASE62_DIVIDER])
            num //= BASE62_DIVIDER

        return ''.join(reversed(base62))

    def from_base62(short_code):
        """
        Декодирует base62-строку обратно в число.

        Args:
            short_code (str): base62-строка

        Returns:
            int: Декодированное число
        """
        num = 0
        for char in short_code:
            num = num * BASE62_DIVIDER + BASE62_ALPHABET.index(char)
        return num
