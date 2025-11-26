"""
analytics tasks for Celery
"""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.analytics_tasks.placeholder")
def placeholder_task():
    """Placeholder task - implement as needed"""
    pass
