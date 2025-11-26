"""
Shipment and logistics models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class ShipmentStatus(str, enum.Enum):
    """Shipment status types"""
    CREATED = "created"
    PICKUP_SCHEDULED = "pickup_scheduled"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RTO = "rto"
    CANCELLED = "cancelled"


class Shipment(TenantBaseModel):
    """Shipment model"""

    __tablename__ = "shipments"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Shipment Info
    awb_number = Column(String(100), nullable=True, index=True)  # Air Waybill Number
    courier_name = Column(String(100), nullable=True)
    courier_id = Column(String(100), nullable=True)

    # Status
    status = Column(SQLEnum(ShipmentStatus), default=ShipmentStatus.CREATED, nullable=False)
    current_location = Column(String(255), nullable=True)

    # Tracking
    tracking_url = Column(String(500), nullable=True)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=True)

    # Weight Reconciliation
    declared_weight = Column(DECIMAL(10, 3), nullable=True)  # kg
    charged_weight = Column(DECIMAL(10, 3), nullable=True)  # kg
    volumetric_weight = Column(DECIMAL(10, 3), nullable=True)  # kg
    weight_discrepancy = Column(Boolean, default=False)

    # Charges
    shipping_charge = Column(DECIMAL(10, 2), nullable=True)
    cod_charge = Column(DECIMAL(10, 2), nullable=True)
    rto_charge = Column(DECIMAL(10, 2), nullable=True)
    total_charge = Column(DECIMAL(10, 2), nullable=True)

    # Timestamps
    pickup_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    rto_initiated_at = Column(DateTime(timezone=True), nullable=True)
    rto_delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Tracking Events
    tracking_events = Column(JSON, default=[])  # [{status, location, timestamp, description}]

    # Metadata
    shiprocket_shipment_id = Column(String(100), nullable=True)
    shiprocket_order_id = Column(String(100), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="shipment")
    ndr_reports = relationship("NDRReport", back_populates="shipment", cascade="all, delete-orphan")


class NDRReport(TenantBaseModel):
    """Non-Delivery Report (NDR) model"""

    __tablename__ = "ndr_reports"

    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)

    # NDR Info
    ndr_date = Column(DateTime(timezone=True), nullable=False)
    ndr_reason = Column(String(255), nullable=False)
    ndr_status = Column(String(50), nullable=False)  # open, resolved, escalated

    # Action Taken
    action_taken = Column(String(100), nullable=True)  # reattempt, reschedule, rto
    action_date = Column(DateTime(timezone=True), nullable=True)

    # Customer Response
    customer_contacted = Column(Boolean, default=False)
    customer_response = Column(Text, nullable=True)
    reattempt_date = Column(DateTime(timezone=True), nullable=True)

    # Resolution
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationship
    shipment = relationship("Shipment", back_populates="ndr_reports")
