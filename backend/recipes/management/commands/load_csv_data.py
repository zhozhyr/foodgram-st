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
                Recipe.objects.create(
                    id=row['id'],
                    name=row['name'],
                    image=row['image'],
                    text=row['text'],
                    cooking_time=row['cooking_time'],
                    pub_date=parse(row['pub_date']),
                    author_id=row['author_id']
                )

        # --- INGREDIENTS ---
        with open(data_dir / 'ingredients.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Ingredient.objects.get_or_create(
                    id=row['id'],
                    name=row['name'],
                    measurement_unit=row['measurement_unit']
                )

        # --- RECIPE COMPONENTS ---
        with open(data_dir / 'recipes_ingredient.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                RecipeComponent.objects.create(
                    id=row['id'],
                    amount=row['amount'],
                    ingredient_id=row['ingredient_id'],
                    recipe_id=row['recipe_id']
                )

        self.stdout.write(self.style.SUCCESS('Данные загружены из CSV'))
