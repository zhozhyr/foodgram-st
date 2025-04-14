import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from users.models import User
from recipes.models import Recipe, RecipeComponent, Ingredient
from dateutil.parser import parse

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Command(BaseCommand):
    """
    Команда для загрузки данных из CSV файлов в базу данных.

    CSV-файлы должны находиться по пути /app/data и иметь следующие имена:
    - users.csv
    - recipes.csv
    - ingredients.csv
    - recipes_ingredient.csv

    Формат данных должен соответствовать структурам моделей:
    - User
    - Recipe
    - Ingredient
    - RecipeComponent
    """
    help = 'Загрузка данных из CSV в базу'

    def handle(self, *args, **kwargs):
        data_dir = Path('/app/data')

        # --- USERS ---
        with open(data_dir / 'users.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                User.objects.create(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password=row['password'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    is_active=True,
                    is_staff=row.get('is_staff', 'False') == 'True',
                    is_superuser=row.get('is_superuser', 'False') == 'True',
                    date_joined=parse(row['date_joined']),
                )

        # --- RECIPES ---
        with open(data_dir / 'recipes.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['cooking_time'] = int(row['cooking_time'])
                row['pub_date'] = parse(row['pub_date'])
                Recipe.objects.create(**row)

        # --- INGREDIENTS ---
        with open(data_dir / 'ingredients.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Ingredient.objects.get_or_create(**row)

        # --- RECIPE COMPONENTS ---
        with open(data_dir / 'recipes_ingredient.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['amount'] = int(row['amount'])
                RecipeComponent.objects.create(**row)

        self.stdout.write(self.style.SUCCESS('Данные загружены из CSV'))
