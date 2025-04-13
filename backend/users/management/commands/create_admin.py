from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Создаёт суперпользователя'

    def handle(self, *args, **options):
        User = get_user_model()
        email = 'admin@admin.ru'
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                username='admin',
                email=email,
                password='admin'
            )
            self.stdout.write(self.style.SUCCESS('Суперпользователь создан'))
        else:
            self.stdout.write('Суперпользователь уже существует')
