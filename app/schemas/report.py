"""
Report schemas
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ReportType(str, Enum):
    """Report types"""

    SALES = "sales"
    PRODUCT_PERFORMANCE = "product_performance"
    GST = "gst"
    PL_BY_CHANNEL = "pl_by_channel"
    RTO_ANALYSIS = "rto_analysis"
    INVENTORY = "inventory"
    FORECAST = "forecast"
    MARKETING_PERFORMANCE = "marketing_performance"
    CUSTOMER_ANALYTICS = "customer_analytics"


class ReportFormat(str, Enum):
    """Report export formats"""

    EXCEL = "excel"
    CSV = "csv"
    PDF = "pdf"


class ReportStatus(str, Enum):
    """Report generation status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleFrequency(str, Enum):
    """Schedule frequency"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportCreate(BaseModel):
    """Create report request"""

    report_type: ReportType
    start_date: date
    end_date: date
    format: ReportFormat = Field(default=ReportFormat.EXCEL)
    filters: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class ReportResponse(BaseModel):
    """Report response"""

    id: int
    report_type: str
    status: str
    start_date: date
    end_date: date
    format: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportScheduleCreate(BaseModel):
    """Create report schedule"""

    report_type: ReportType
    frequency: ScheduleFrequency
    format: ReportFormat = Field(default=ReportFormat.EXCEL)
    recipients: List[str] = Field(..., min_items=1)
    filters: Optional[Dict[str, Any]] = None
    is_active: bool = Field(default=True)

    class Config:
        use_enum_values = True


class ReportScheduleUpdate(BaseModel):
    """Update report schedule"""

    frequency: Optional[ScheduleFrequency] = None
    format: Optional[ReportFormat] = None
    recipients: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    class Config:
        use_enum_values = True


class ReportScheduleResponse(BaseModel):
    """Report schedule response"""

    id: int
    report_type: str
    frequency: str
    format: str
    recipients: List[str]
    filters: Optional[Dict[str, Any]] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
