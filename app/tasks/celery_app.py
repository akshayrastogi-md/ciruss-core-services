"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "d2c_analytics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Channel sync every 30 minutes
    "sync-channels": {
        "task": "app.tasks.channel_tasks.sync_all_channels",
        "schedule": crontab(minute="*/30"),
    },
    # Daily analytics aggregation at 1 AM
    "daily-analytics": {
        "task": "app.tasks.analytics_tasks.aggregate_daily_metrics",
        "schedule": crontab(hour=1, minute=0),
    },
    # ML model training every Sunday at 2 AM
    "train-ml-models": {
        "task": "app.tasks.ml_tasks.train_all_models",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
    # Pincode metrics update daily at 3 AM
    "update-pincode-metrics": {
        "task": "app.tasks.analytics_tasks.update_pincode_metrics",
        "schedule": crontab(hour=3, minute=0),
    },
    # Inventory snapshot daily at 4 AM
    "inventory-snapshot": {
        "task": "app.tasks.inventory_tasks.create_daily_snapshots",
        "schedule": crontab(hour=4, minute=0),
    },
    # Stock alerts check every 6 hours
    "check-stock-alerts": {
        "task": "app.tasks.inventory_tasks.check_stock_alerts",
        "schedule": crontab(hour="*/6", minute=0),
    },
    # COD remittance tracking daily at 10 AM
    "track-cod-remittances": {
        "task": "app.tasks.payment_tasks.track_cod_remittances",
        "schedule": crontab(hour=10, minute=0),
    },
    # Subscription usage check hourly
    "check-subscription-usage": {
        "task": "app.tasks.subscription_tasks.check_usage_limits",
        "schedule": crontab(minute=0),
    },
}

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.channel_tasks.*": {"queue": "high_priority"},
    "app.tasks.ml_tasks.*": {"queue": "low_priority"},
    "app.tasks.report_tasks.*": {"queue": "low_priority"},
}

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "app.tasks.channel_tasks",
    "app.tasks.analytics_tasks",
    "app.tasks.ml_tasks",
    "app.tasks.inventory_tasks",
    "app.tasks.payment_tasks",
    "app.tasks.report_tasks",
    "app.tasks.subscription_tasks",
])
