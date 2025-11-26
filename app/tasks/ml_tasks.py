"""
ml tasks for Celery
"""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.ml_tasks.placeholder")
def placeholder_task():
    """Placeholder task - implement as needed"""
    pass
