# Foodgram
«Фудграм» — сайт, на котором пользователи могут публиковать свои рецепты, добавлять чужие в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Возможности

- Регистрация, авторизация
- Создание, редактирование и удаление рецептов
- Фильтрация по ингредиентам, тегам, авторам
- Добавление рецептов в избранное и список покупок
- Подписка на авторов
- Скачивание списка покупок
- Админ-панель для управления данными

## Для запуска проекта:

- Клонируйте репозиторий с проектом на свой компьютер: https://github.com/zhozhyr/foodgram-st
- Создайте в директории foodgram/backend файл .env и заполните его

```commandline
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=foodgram-db
DB_PORT=5432
```

- Перейдите в папку infra/
```commandline
cc ..
cd .\infra\
```
- Запустите сборку проекта:
```commandline
docker-compose up --build
```
Миграции, импорт базы данных выполнятся автоматически.

## Для тестирования функционала системы были заданы 4 пользователя:
#### Администратор

- email: admin@admin.ru
- пароль: admin

#### Пользователь №1
- email: user1@user.ru
- пароль: qwertyuiop1234
#### Пользователь №2
- email: user4@user4.user4
- пароль: qwertyuiop4
#### Пользователь №3
- email: user3@user.ru
- пароль: qwertyuiop12345

## Примеры API-запросов

- Получение токена
```commandline
POST /api/token/login/
```
```commandline
{
  "email": "user1@user.ru",
  "password": "qwertyuiop1234"
}

```
- Получение рецептов
```commandline
GET /api/recipes/
```
- Добавление рецепта
```commandline
POST /api/recipes/
```
```commandline
{
  "name": "Омлет",
  "text": "Взбить яйца, обжарить",
  "cooking_time": 10,
  "ingredients": [
    {"id": 1, "amount": 2},
    {"id": 2, "amount": 50}
  ],
  "tags": [1, 2],
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."
}

```

### Стэк:
Python, DRF, PostgreSQL, Docker, NGINX, Gunicorn, GitHub Actions, CI/CD  

### Docker Hub
```
https://hub.docker.com/r/zjozjyr/foodgram-backend
```
Образ foodgram-backend

### Автор
zhozhyr - https://github.com/zhozhyr


