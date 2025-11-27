"""
Reports endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.report_service import ReportService
from app.schemas.report import (
    ReportCreate,
    ReportResponse,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportScheduleResponse,
)

router = APIRouter()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    report_data: ReportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new report

    Creates a report generation task. The report will be generated in the background
    and the file URL will be available once complete.
    """
    service = ReportService(db, current_user.tenant_id)

    report = await service.create_report(
        report_type=report_data.report_type,
        start_date=report_data.start_date,
        end_date=report_data.end_date,
        format=report_data.format,
        filters=report_data.filters,
    )

    # Queue background task for report generation
    # background_tasks.add_task(generate_report_task, report.id, current_user.tenant_id)

    return ReportResponse(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        start_date=report.start_date,
        end_date=report.end_date,
        format=report.format,
        file_url=report.file_url,
        file_size=report.file_size,
        error_message=report.error_message,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all reports

    Returns a list of generated reports with optional filtering by type and status.
    """
    service = ReportService(db, current_user.tenant_id)
    reports = await service.list_reports(
        report_type=report_type, status=status, limit=limit, offset=offset
    )

    return [
        ReportResponse(
            id=report.id,
            report_type=report.report_type,
            status=report.status,
            start_date=report.start_date,
            end_date=report.end_date,
            format=report.format,
            file_url=report.file_url,
            file_size=report.file_size,
            error_message=report.error_message,
            created_at=report.created_at,
            completed_at=report.completed_at,
        )
        for report in reports
    ]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific report

    Returns details of a specific report including download URL if available.
    """
    service = ReportService(db, current_user.tenant_id)
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        start_date=report.start_date,
        end_date=report.end_date,
        format=report.format,
        file_url=report.file_url,
        file_size=report.file_size,
        error_message=report.error_message,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


@router.post("/schedules", response_model=ReportScheduleResponse)
async def create_schedule(
    schedule_data: ReportScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a report schedule

    Sets up automatic report generation on a recurring basis (daily, weekly, or monthly).
    """
    service = ReportService(db, current_user.tenant_id)

    schedule = await service.create_schedule(
        report_type=schedule_data.report_type,
        frequency=schedule_data.frequency,
        format=schedule_data.format,
        recipients=schedule_data.recipients,
        filters=schedule_data.filters,
    )

    return ReportScheduleResponse(
        id=schedule.id,
        report_type=schedule.report_type,
        frequency=schedule.frequency,
        format=schedule.format,
        recipients=schedule.recipients,
        filters=schedule.filters,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.get("/schedules/", response_model=List[ReportScheduleResponse])
async def list_schedules(
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List report schedules

    Returns all configured report schedules.
    """
    service = ReportService(db, current_user.tenant_id)
    schedules = await service.list_schedules(
        is_active=is_active, limit=limit, offset=offset
    )

    return [
        ReportScheduleResponse(
            id=schedule.id,
            report_type=schedule.report_type,
            frequency=schedule.frequency,
            format=schedule.format,
            recipients=schedule.recipients,
            filters=schedule.filters,
            is_active=schedule.is_active,
            last_run_at=schedule.last_run_at,
            next_run_at=schedule.next_run_at,
            created_at=schedule.created_at,
        )
        for schedule in schedules
    ]


@router.get("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
async def get_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific report schedule
    """
    service = ReportService(db, current_user.tenant_id)
    schedule = await service.get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ReportScheduleResponse(
        id=schedule.id,
        report_type=schedule.report_type,
        frequency=schedule.frequency,
        format=schedule.format,
        recipients=schedule.recipients,
        filters=schedule.filters,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.patch("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ReportScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a report schedule

    Modify scheduling parameters, recipients, or activate/deactivate the schedule.
    """
    service = ReportService(db, current_user.tenant_id)

    schedule = await service.update_schedule(
        schedule_id=schedule_id,
        frequency=schedule_data.frequency,
        format=schedule_data.format,
        recipients=schedule_data.recipients,
        filters=schedule_data.filters,
        is_active=schedule_data.is_active,
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ReportScheduleResponse(
        id=schedule.id,
        report_type=schedule.report_type,
        frequency=schedule.frequency,
        format=schedule.format,
        recipients=schedule.recipients,
        filters=schedule.filters,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a report schedule

    Permanently removes a report schedule.
    """
    service = ReportService(db, current_user.tenant_id)
    success = await service.delete_schedule(schedule_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"message": "Schedule deleted successfully"}
