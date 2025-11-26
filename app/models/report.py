"""
Report models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum, JSON, Text
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class ReportType(str, enum.Enum):
    """Report types"""
    SALES = "sales"
    PRODUCT_PERFORMANCE = "product_performance"
    GST = "gst"
    PNL_BY_CHANNEL = "pnl_by_channel"
    RTO_ANALYSIS = "rto_analysis"
    INVENTORY = "inventory"
    FORECAST = "forecast"
    MARKETING_PERFORMANCE = "marketing_performance"


class ReportStatus(str, enum.Enum):
    """Report generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(TenantBaseModel):
    """Generated report model"""

    __tablename__ = "reports"

    # Report Info
    name = Column(String(500), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)

    # Status
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    # Parameters
    parameters = Column(JSON, default={})  # {date_from, date_to, filters}

    # Output
    file_format = Column(String(20), nullable=True)  # excel, csv, pdf
    file_url = Column(String(1000), nullable=True)  # S3 URL
    file_size = Column(Integer, nullable=True)  # in bytes

    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Error
    error_message = Column(Text, nullable=True)

    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    schedule = relationship("ReportSchedule", back_populates="reports")


class ReportSchedule(TenantBaseModel):
    """Report schedule model"""

    __tablename__ = "report_schedules"

    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)

    # Schedule Info
    name = Column(String(500), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)

    # Schedule
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly
    time = Column(String(10), nullable=False)  # HH:MM
    day_of_week = Column(Integer, nullable=True)  # 0-6 for weekly
    day_of_month = Column(Integer, nullable=True)  # 1-31 for monthly

    # Parameters
    parameters = Column(JSON, default={})
    file_format = Column(String(20), default="excel")

    # Recipients
    recipients = Column(JSON, default=[])  # List of email addresses

    # Status
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reports = relationship("Report", back_populates="schedule")
