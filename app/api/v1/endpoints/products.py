"""
Products API endpoints - Complete CRUD implementation
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.product import Product, ProductVariant, HSNCode

router = APIRouter()


# Schemas
class ProductCreate(BaseModel):
    """Product creation schema"""
    name: str = Field(..., min_length=1, max_length=500)
    sku: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    total_stock: int = 0
    safety_stock: int = 0
    weight: Optional[Decimal] = None
    hsn_code_id: Optional[int] = None
    tax_rate: Decimal = Decimal("18.00")
    image_url: Optional[str] = None
    tags: List[str] = []


class ProductUpdate(BaseModel):
    """Product update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    total_stock: Optional[int] = None
    safety_stock: Optional[int] = None
    weight: Optional[Decimal] = None
    hsn_code_id: Optional[int] = None
    tax_rate: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None
    tags: Optional[List[str]] = None


class ProductResponse(BaseModel):
    """Product response schema"""
    id: int
    name: str
    sku: str
    description: Optional[str]
    category: Optional[str]
    brand: Optional[str]
    cost_price: Optional[Decimal]
    selling_price: Optional[Decimal]
    mrp: Optional[Decimal]
    total_stock: int
    safety_stock: int
    weight: Optional[Decimal]
    tax_rate: Decimal
    image_url: Optional[str]
    is_active: bool
    is_published: bool
    tags: List[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Product list response with pagination"""
    total: int
    page: int
    page_size: int
    products: List[ProductResponse]


# Endpoints
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new product
    """
    # Check if SKU already exists for this tenant
    result = await db.execute(
        select(Product).where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                Product.sku == product_data.sku,
            )
        )
    )
    existing_product = result.scalar_one_or_none()

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_data.sku}' already exists",
        )

    # Create product
    product = Product(
        tenant_id=current_user.tenant_id,
        **product_data.model_dump(),
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product


@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    low_stock: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all products with pagination and filters
    """
    # Build query
    query = select(Product).where(Product.tenant_id == current_user.tenant_id)

    # Apply filters
    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )

    if category:
        query = query.where(Product.category == category)

    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    if is_published is not None:
        query = query.where(Product.is_published == is_published)

    if low_stock:
        query = query.where(Product.total_stock <= Product.safety_stock)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Product.created_at.desc())

    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        total=total,
        page=page,
        page_size=page_size,
        products=products,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific product by ID
    """
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_id == current_user.tenant_id,
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a product
    """
    # Get product
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_id == current_user.tenant_id,
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a product (soft delete by setting is_active=False)
    """
    # Get product
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_id == current_user.tenant_id,
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Soft delete
    product.is_active = False
    await db.commit()


@router.post("/{product_id}/stock-adjustment")
async def adjust_stock(
    product_id: int,
    adjustment: int,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Adjust product stock
    """
    # Get product
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_id == current_user.tenant_id,
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Adjust stock
    new_stock = product.total_stock + adjustment

    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock",
        )

    product.total_stock = new_stock
    await db.commit()

    return {
        "product_id": product_id,
        "previous_stock": product.total_stock - adjustment,
        "adjustment": adjustment,
        "new_stock": new_stock,
        "reason": reason,
    }


@router.get("/categories/list")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all product categories
    """
    result = await db.execute(
        select(Product.category, func.count(Product.id).label('count'))
        .where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                Product.category.isnot(None),
            )
        )
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
    )

    categories = [
        {"name": row[0], "count": row[1]}
        for row in result.all()
    ]

    return {"categories": categories}


@router.get("/low-stock/alert")
async def get_low_stock_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get products with low stock (below safety stock level)
    """
    result = await db.execute(
        select(Product).where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                Product.total_stock <= Product.safety_stock,
                Product.is_active == True,
            )
        ).order_by(Product.total_stock.asc())
    )

    products = result.scalars().all()

    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "current_stock": p.total_stock,
                "safety_stock": p.safety_stock,
                "deficit": p.safety_stock - p.total_stock,
            }
            for p in products
        ],
    }


@router.post("/bulk-import")
async def bulk_import_products(
    products: List[ProductCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import products
    """
    created_count = 0
    skipped_count = 0
    errors = []

    for idx, product_data in enumerate(products):
        try:
            # Check if SKU exists
            result = await db.execute(
                select(Product).where(
                    and_(
                        Product.tenant_id == current_user.tenant_id,
                        Product.sku == product_data.sku,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                skipped_count += 1
                continue

            # Create product
            product = Product(
                tenant_id=current_user.tenant_id,
                **product_data.model_dump(),
            )
            db.add(product)
            created_count += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "sku": product_data.sku,
                "error": str(e),
            })

    await db.commit()

    return {
        "created": created_count,
        "skipped": skipped_count,
        "errors": errors,
        "total": len(products),
    }
