FROM python:3.13

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD sh -c "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py load_csv_data && python manage.py create_admin && gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000"
