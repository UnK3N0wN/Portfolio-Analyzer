import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio_ai.settings')

app = Celery('portfolio_ai')

# Read CELERY_* settings from Django settings.py (namespace='CELERY' means
# e.g. CELERY_BROKER_URL maps to the `broker_url` Celery setting).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover a `tasks.py` in each installed app (portfolio/tasks.py etc).
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')