"""
Report tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import datetime, timedelta


@celery_app.task(name="app.tasks.report_tasks.generate_scheduled_reports")
def generate_scheduled_reports():
    """
    Generate scheduled reports

    Runs hourly to check for scheduled reports that need to be generated.
    """
    from app.db.session import get_sync_db
    from app.models.report import ReportSchedule, Report
    from sqlalchemy import select, and_

    db = next(get_sync_db())

    try:
        now = datetime.utcnow()

        # Get all active schedules that are due
        schedules = db.execute(
            select(ReportSchedule).where(
                and_(
                    ReportSchedule.is_active == True,
                    ReportSchedule.next_run_at <= now,
                )
            )
        ).scalars().all()

        reports_generated = 0

        for schedule in schedules:
            # Calculate date range
            if schedule.frequency == "daily":
                start_date = (now - timedelta(days=1)).date()
                end_date = (now - timedelta(days=1)).date()
                next_run = now + timedelta(days=1)
            elif schedule.frequency == "weekly":
                start_date = (now - timedelta(days=7)).date()
                end_date = (now - timedelta(days=1)).date()
                next_run = now + timedelta(days=7)
            elif schedule.frequency == "monthly":
                start_date = (now - timedelta(days=30)).date()
                end_date = (now - timedelta(days=1)).date()
                next_run = now + timedelta(days=30)
            else:
                continue

            # Create report
            report = Report(
                tenant_id=schedule.tenant_id,
                report_type=schedule.report_type,
                start_date=start_date,
                end_date=end_date,
                format=schedule.format,
                filters=schedule.filters or {},
                status="pending",
            )
            db.add(report)
            reports_generated += 1

            # Update schedule
            schedule.last_run_at = now
            schedule.next_run_at = next_run

        db.commit()

        return {
            "status": "success",
            "reports_generated": reports_generated,
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
