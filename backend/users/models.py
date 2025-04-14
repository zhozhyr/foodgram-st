from django.contrib.auth.models import AbstractUser
from django.db import models

from foodgram.constants import (MAX_LENGTH_USER_FIRST_NAME,
                                MAX_LENGTH_USER_LAST_NAME)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    first_name = models.CharField(
        max_length=MAX_LENGTH_USER_FIRST_NAME,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_USER_LAST_NAME,
        verbose_name='Фамилия'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Электронная почта',
        error_messages={
            'unique': 'Пользователь с таким email уже существует.',
        }
    )
    avatar = models.ImageField(
        upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return self.username


class Subscription(models.Model):
    follower = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='subscribers',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['follower']
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'author'],
                name='unique_user_following',
            )
        ]

    def __str__(self):
        return f'{self.follower} подписан на {self.author}'
