import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_hunt.settings')
app=Celery('web')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "daily-python-vacancies":{
        "tasks":"tracker.tasks.scrape_vacancies.task",
        "schedule":crontab(hour=8,minute=0),
        "args":("Python",),
    },
}