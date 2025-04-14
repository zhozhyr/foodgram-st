from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subscription

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')

    @admin.display(description='Рецептов')
    def recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписчиков')
    def subscribers_count(self, obj):
        return obj.subscribers.count()


@admin.register(Subscription)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'author')
    list_filter = ('follower', 'author')
    search_fields = ('follower__username', 'author__username')
    raw_id_fields = ('follower', 'author')
