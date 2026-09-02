FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary needs libpq at runtime; build-essential covers anything
# else that needs compiling on install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "portfolio_ai.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]