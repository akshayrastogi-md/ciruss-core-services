"""
Payment reconciliation models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Date, Enum as SQLEnum, Text, Index
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class ReconciliationStatus(str, enum.Enum):
    """Reconciliation status"""
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    MISSING_IN_PLATFORM = "missing_in_platform"
    MISSING_IN_SYSTEM = "missing_in_system"
    RESOLVED = "resolved"


class PaymentReconciliation(TenantBaseModel):
    """Payment reconciliation model"""

    __tablename__ = "payment_reconciliations"
    __table_args__ = (
        Index("idx_payment_recon_tenant_date", "tenant_id", "settlement_date"),
    )

    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)

    # Settlement Info
    settlement_date = Column(Date, nullable=False)
    settlement_id = Column(String(255), nullable=True)

    # Order Info
    platform_order_id = Column(String(255), nullable=True)
    system_order_number = Column(String(100), nullable=True)

    # Amounts
    platform_amount = Column(DECIMAL(10, 2), nullable=True)
    system_amount = Column(DECIMAL(10, 2), nullable=True)
    difference = Column(DECIMAL(10, 2), nullable=True)

    # Status
    status = Column(SQLEnum(ReconciliationStatus), nullable=False)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Metadata
    platform_data = Column(Text, nullable=True)  # JSON from platform report

    # Relationships
    channel = relationship("Channel", foreign_keys=[channel_id])
    order = relationship("Order", foreign_keys=[order_id])


class CODRemittance(TenantBaseModel):
    """COD remittance tracking"""

    __tablename__ = "cod_remittances"
    __table_args__ = (
        Index("idx_cod_remittance_tenant_channel", "tenant_id", "channel_id"),
    )

    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)

    # Remittance Info
    remittance_date = Column(Date, nullable=True)
    expected_remittance_date = Column(Date, nullable=False)
    settlement_cycle_days = Column(Integer, nullable=False)  # T+2, T+7, T+14

    # Amounts
    total_cod_orders = Column(Integer, default=0)
    total_cod_amount = Column(DECIMAL(12, 2), default=0)
    remitted_amount = Column(DECIMAL(12, 2), nullable=True)
    pending_amount = Column(DECIMAL(12, 2), default=0)

    # Deductions
    platform_commission = Column(DECIMAL(10, 2), default=0)
    shipping_charges = Column(DECIMAL(10, 2), default=0)
    cod_charges = Column(DECIMAL(10, 2), default=0)
    other_deductions = Column(DECIMAL(10, 2), default=0)
    total_deductions = Column(DECIMAL(10, 2), default=0)

    # Net Amount
    net_remittance = Column(DECIMAL(12, 2), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, received, delayed, disputed
    is_delayed = Column(Boolean, default=False)
    delay_days = Column(Integer, default=0)

    # Alert
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationship
    channel = relationship("Channel", foreign_keys=[channel_id])
