"""
Product and inventory models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, Text, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel, BaseModel


class Product(TenantBaseModel):
    """Product model"""

    __tablename__ = "products"
    __table_args__ = (
        Index("idx_product_tenant_sku", "tenant_id", "sku"),
    )

    # Basic Info
    name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    brand = Column(String(100), nullable=True)

    # Pricing
    cost_price = Column(DECIMAL(10, 2), nullable=True)  # COGS
    selling_price = Column(DECIMAL(10, 2), nullable=True)
    mrp = Column(DECIMAL(10, 2), nullable=True)

    # Inventory
    total_stock = Column(Integer, default=0)
    safety_stock = Column(Integer, default=0)
    reorder_point = Column(Integer, default=0)

    # Physical Properties
    weight = Column(DECIMAL(10, 3), nullable=True)  # in kg
    length = Column(DECIMAL(10, 2), nullable=True)  # in cm
    width = Column(DECIMAL(10, 2), nullable=True)
    height = Column(DECIMAL(10, 2), nullable=True)

    # GST
    hsn_code_id = Column(Integer, ForeignKey("hsn_codes.id"), nullable=True)
    tax_rate = Column(DECIMAL(5, 2), default=18.00)  # GST %

    # Status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=True)

    # Multi-channel mapping
    channel_mappings = Column(JSON, default={})  # {channel_id: external_product_id}

    # Images
    image_url = Column(String(1000), nullable=True)
    images = Column(JSON, default=[])

    # Metadata
    tags = Column(JSON, default=[])
    custom_fields = Column(JSON, default={})

    # Relationships
    tenant = relationship("Tenant", back_populates="products")
    hsn_code = relationship("HSNCode", foreign_keys=[hsn_code_id])
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")


class ProductVariant(TenantBaseModel):
    """Product variant model"""

    __tablename__ = "product_variants"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    # Variant Info
    name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    variant_attributes = Column(JSON, default={})  # {color: "Red", size: "M"}

    # Pricing
    cost_price = Column(DECIMAL(10, 2), nullable=True)
    selling_price = Column(DECIMAL(10, 2), nullable=True)
    mrp = Column(DECIMAL(10, 2), nullable=True)

    # Inventory
    stock = Column(Integer, default=0)

    # Physical Properties
    weight = Column(DECIMAL(10, 3), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Multi-channel mapping
    channel_mappings = Column(JSON, default={})

    # Image
    image_url = Column(String(1000), nullable=True)

    # Relationship
    product = relationship("Product", back_populates="variants")


class HSNCode(BaseModel):
    """HSN Code master for GST"""

    __tablename__ = "hsn_codes"

    code = Column(String(8), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)

    # GST Rates
    cgst_rate = Column(DECIMAL(5, 2), nullable=False)
    sgst_rate = Column(DECIMAL(5, 2), nullable=False)
    igst_rate = Column(DECIMAL(5, 2), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
