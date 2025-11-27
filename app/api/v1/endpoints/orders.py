"""
Orders API endpoints - Complete CRUD implementation
"""
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from pydantic import BaseModel, Field, EmailStr
from decimal import Decimal

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.services.ml.rto_prediction import RTOPredictionService
from app.services.gst.tax_calculator import GSTCalculator

router = APIRouter()


# Schemas
class OrderItemCreate(BaseModel):
    """Order item creation schema"""
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Optional[Decimal] = None


class OrderCreate(BaseModel):
    """Order creation schema"""
    customer_name: str = Field(..., min_length=1)
    customer_email: Optional[EmailStr] = None
    customer_phone: str = Field(..., min_length=10)
    shipping_address_line1: str
    shipping_city: str
    shipping_state: str
    shipping_pincode: str = Field(..., min_length=6, max_length=6)
    billing_address_line1: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_pincode: Optional[str] = None
    payment_method: PaymentMethod
    items: List[OrderItemCreate]
    discount_amount: Decimal = Decimal("0")
    shipping_charges: Decimal = Decimal("0")
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response schema"""
    id: int
    order_number: str
    order_date: str
    status: OrderStatus
    customer_name: str
    customer_email: Optional[str]
    customer_phone: str
    payment_method: PaymentMethod
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_charges: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    rto_risk_score: Optional[int]
    rto_risk_level: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Order list response with pagination"""
    total: int
    page: int
    page_size: int
    orders: List[OrderResponse]


class OrderDetailResponse(OrderResponse):
    """Detailed order response with items"""
    items: List[dict]
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    shipping_address: dict
    billing_address: dict


# Endpoints
@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order with automatic tax calculation and RTO prediction
    """
    # Generate order number
    order_count = await db.execute(
        select(func.count(Order.id)).where(Order.tenant_id == current_user.tenant_id)
    )
    count = order_count.scalar() + 1
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{count:05d}"

    # Calculate order totals
    subtotal = Decimal("0")
    tax_calculator = GSTCalculator()

    # Billing address defaults to shipping if not provided
    billing_city = order_data.billing_city or order_data.shipping_city
    billing_state = order_data.billing_state or order_data.shipping_state
    billing_pincode = order_data.billing_pincode or order_data.shipping_pincode

    # Create order
    order = Order(
        tenant_id=current_user.tenant_id,
        order_number=order_number,
        order_date=datetime.utcnow(),
        status=OrderStatus.PENDING,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        customer_phone=order_data.customer_phone,
        shipping_address_line1=order_data.shipping_address_line1,
        shipping_city=order_data.shipping_city,
        shipping_state=order_data.shipping_state,
        shipping_pincode=order_data.shipping_pincode,
        billing_address_line1=order_data.billing_address_line1 or order_data.shipping_address_line1,
        billing_city=billing_city,
        billing_state=billing_state,
        billing_pincode=billing_pincode,
        payment_method=order_data.payment_method,
        payment_status="pending",
        discount_amount=order_data.discount_amount,
        shipping_charges=order_data.shipping_charges,
        notes=order_data.notes,
    )

    db.add(order)
    await db.flush()

    # Add order items and calculate taxes
    total_cgst = Decimal("0")
    total_sgst = Decimal("0")
    total_igst = Decimal("0")

    for item_data in order_data.items:
        # Get product
        result = await db.execute(
            select(Product).where(
                and_(
                    Product.id == item_data.product_id,
                    Product.tenant_id == current_user.tenant_id,
                )
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_data.product_id} not found",
            )

        # Use product selling price if not provided
        unit_price = item_data.unit_price or product.selling_price

        # Calculate GST
        gst_calc = await tax_calculator.calculate_gst(
            db=db,
            tenant_id=current_user.tenant_id,
            product_id=product.id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            billing_state=billing_state,
            shipping_state=order_data.shipping_state,
        )

        # Create order item
        order_item = OrderItem(
            tenant_id=current_user.tenant_id,
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            unit_price=unit_price,
            quantity=item_data.quantity,
            unit_cost=product.cost_price,
            tax_rate=Decimal(str(gst_calc['cgst_rate'] + gst_calc['sgst_rate'])) if gst_calc['cgst_amount'] > 0 else Decimal(str(gst_calc['igst_rate'])),
            tax_amount=Decimal(str(gst_calc['total_tax'])),
            cgst_amount=Decimal(str(gst_calc['cgst_amount'])),
            sgst_amount=Decimal(str(gst_calc['sgst_amount'])),
            igst_amount=Decimal(str(gst_calc['igst_amount'])),
            total_amount=Decimal(str(gst_calc['total_amount'])),
        )
        db.add(order_item)

        subtotal += Decimal(str(gst_calc['base_amount']))
        total_cgst += Decimal(str(gst_calc['cgst_amount']))
        total_sgst += Decimal(str(gst_calc['sgst_amount']))
        total_igst += Decimal(str(gst_calc['igst_amount']))

    # Update order totals
    order.subtotal = subtotal
    order.tax_amount = total_cgst + total_sgst + total_igst
    order.cgst_amount = total_cgst
    order.sgst_amount = total_sgst
    order.igst_amount = total_igst
    order.total_amount = subtotal - order.discount_amount + order.shipping_charges + order.tax_amount

    # RTO Prediction for COD orders
    if order.payment_method == PaymentMethod.COD:
        try:
            rto_service = RTOPredictionService()
            prediction = await rto_service.predict({
                "total_amount": float(order.total_amount),
                "payment_method": "cod",
                "customer_type": "new",  # TODO: Check from order history
                "pincode": order.shipping_pincode,
                "category": "general",
                "day_of_week": datetime.now().weekday(),
            })

            order.rto_probability = Decimal(str(prediction['rto_probability']))
            order.rto_risk_score = prediction['risk_score']
            order.rto_risk_level = prediction['risk_level']

        except Exception as e:
            # If RTO prediction fails, continue without it
            print(f"RTO prediction failed: {e}")

    await db.commit()
    await db.refresh(order)

    return order


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    payment_method: Optional[PaymentMethod] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all orders with pagination and filters
    """
    # Build query
    query = select(Order).where(Order.tenant_id == current_user.tenant_id)

    # Apply filters
    if status:
        query = query.where(Order.status == status)

    if payment_method:
        query = query.where(Order.payment_method == payment_method)

    if date_from:
        query = query.where(Order.order_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.where(Order.order_date <= datetime.combine(date_to, datetime.max.time()))

    if search:
        query = query.where(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Order.customer_name.ilike(f"%{search}%"),
                Order.customer_phone.ilike(f"%{search}%"),
                Order.customer_email.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Order.order_date.desc())

    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        orders=orders,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed order information
    """
    result = await db.execute(
        select(Order).where(
            and_(
                Order.id == order_id,
                Order.tenant_id == current_user.tenant_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Get order items
    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = items_result.scalars().all()

    return OrderDetailResponse(
        **order.dict(),
        items=[
            {
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_amount": item.tax_amount,
                "total_amount": item.total_amount,
            }
            for item in items
        ],
        shipping_address={
            "line1": order.shipping_address_line1,
            "city": order.shipping_city,
            "state": order.shipping_state,
            "pincode": order.shipping_pincode,
        },
        billing_address={
            "line1": order.billing_address_line1,
            "city": order.billing_city,
            "state": order.billing_state,
            "pincode": order.billing_pincode,
        },
    )


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update order status
    """
    # Get order
    result = await db.execute(
        select(Order).where(
            and_(
                Order.id == order_id,
                Order.tenant_id == current_user.tenant_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Update status
    old_status = order.status
    order.status = new_status

    # Update timestamps based on status
    if new_status == OrderStatus.CONFIRMED:
        order.confirmed_at = datetime.utcnow()
    elif new_status == OrderStatus.SHIPPED:
        order.shipped_at = datetime.utcnow()
    elif new_status == OrderStatus.DELIVERED:
        order.delivered_at = datetime.utcnow()
    elif new_status == OrderStatus.CANCELLED:
        order.cancelled_at = datetime.utcnow()

    await db.commit()

    return {
        "order_id": order_id,
        "old_status": old_status,
        "new_status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/analytics/summary")
async def get_orders_summary(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get orders summary and analytics
    """
    # Build base query
    query = select(Order).where(Order.tenant_id == current_user.tenant_id)

    if date_from:
        query = query.where(Order.order_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.where(Order.order_date <= datetime.combine(date_to, datetime.max.time()))

    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()

    # Calculate metrics
    total_orders = len(orders)
    total_revenue = sum(float(o.total_amount) for o in orders)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    cod_orders = sum(1 for o in orders if o.payment_method == PaymentMethod.COD)
    cod_percentage = (cod_orders / total_orders * 100) if total_orders > 0 else 0

    delivered_orders = sum(1 for o in orders if o.status == OrderStatus.DELIVERED)
    rto_orders = sum(1 for o in orders if o.status == OrderStatus.RTO_DELIVERED)
    rto_rate = (rto_orders / total_orders * 100) if total_orders > 0 else 0

    # Status breakdown
    status_breakdown = {}
    for status in OrderStatus:
        count = sum(1 for o in orders if o.status == status)
        status_breakdown[status.value] = count

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "cod_orders": cod_orders,
        "cod_percentage": cod_percentage,
        "prepaid_orders": total_orders - cod_orders,
        "delivered_orders": delivered_orders,
        "rto_orders": rto_orders,
        "rto_rate": rto_rate,
        "status_breakdown": status_breakdown,
    }


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an order
    """
    # Get order
    result = await db.execute(
        select(Order).where(
            and_(
                Order.id == order_id,
                Order.tenant_id == current_user.tenant_id,
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if order can be cancelled
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {order.status}",
        )

    # Cancel order
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    order.notes = f"{order.notes}\nCancellation reason: {reason}" if order.notes else f"Cancellation reason: {reason}"

    await db.commit()
