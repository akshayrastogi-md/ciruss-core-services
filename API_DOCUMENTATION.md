# D2C Analytics Platform - Complete API Documentation

Version: 3.0
Last Updated: 2025-11-27

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Common Response Formats](#common-response-formats)
5. [Rate Limiting](#rate-limiting)
6. [API Endpoints](#api-endpoints)
   - [Authentication APIs](#authentication-apis)
   - [User Management APIs](#user-management-apis)
   - [Channel Management APIs](#channel-management-apis)
   - [Product Management APIs](#product-management-apis)
   - [Order Management APIs](#order-management-apis)
   - [Analytics APIs](#analytics-apis)
   - [Subscription & Billing APIs](#subscription--billing-apis)
7. [Webhooks](#webhooks)
8. [Error Codes](#error-codes)
9. [Postman Collection](#postman-collection)

---

## Overview

The D2C Analytics Platform provides a comprehensive REST API for managing multi-channel e-commerce operations, including:

- **Multi-tenant Architecture**: Complete tenant isolation
- **4 Channel Integrations**: Shopify, WooCommerce, Amazon, Flipkart
- **ML-Powered Analytics**: RTO prediction, demand forecasting, pin code risk scoring
- **GST Compliance**: Automated tax calculation, invoice generation, GST reports
- **Logistics Integration**: Shiprocket for order fulfillment
- **Subscription Management**: Razorpay integration for billing

---

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Authentication Flow

1. **Register** a new account or **Login** to get access tokens
2. Include the **access token** in the `Authorization` header for all requests
3. **Refresh** the access token when it expires using the refresh token

### Token Lifetime

- **Access Token**: 30 minutes
- **Refresh Token**: 7 days

### Authorization Header Format

```
Authorization: Bearer <access_token>
```

---

## Base URL

### Development
```
http://localhost:8000
```

### Production
```
https://api.ciruss.io
```

### API Version
```
/api/v1
```

---

## Common Response Formats

### Success Response
```json
{
  "id": 123,
  "name": "Product Name",
  "created_at": "2025-01-15T10:30:00Z",
  ...
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Paginated Response
```json
{
  "total": 150,
  "page": 1,
  "page_size": 50,
  "items": [...]
}
```

---

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when the limit resets (Unix timestamp)

---

## API Endpoints

---

## Authentication APIs

### 1. Register New Account

Create a new tenant account with an admin user.

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "company_name": "My D2C Store",
  "gstin": "22AAAAA0000A1Z5",
  "phone": "+91-9876543210"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "tenant_id": 1,
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Notes**:
- Password must be at least 8 characters
- GSTIN format: 15 characters (e.g., 22AAAAA0000A1Z5)
- Email verification email will be sent
- Automatically creates a tenant with the company name

---

### 2. Login

Authenticate and receive access tokens.

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Notes**:
- Access token expires in 30 minutes
- Refresh token expires in 7 days
- Account locks after 5 failed login attempts

---

### 3. Refresh Access Token

Get a new access token using refresh token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### 4. Logout

Invalidate the current access token.

**Endpoint**: `POST /api/v1/auth/logout`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "message": "Successfully logged out"
}
```

---

### 5. Request Password Reset

Send password reset email.

**Endpoint**: `POST /api/v1/auth/password-reset`

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response**: `200 OK`
```json
{
  "message": "Password reset email sent"
}
```

---

### 6. Reset Password

Reset password using token from email.

**Endpoint**: `POST /api/v1/auth/password-reset/confirm`

**Request Body**:
```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123!"
}
```

**Response**: `200 OK`
```json
{
  "message": "Password successfully reset"
}
```

---

## User Management APIs

### 7. Get Current User Profile

Get details of the authenticated user.

**Endpoint**: `GET /api/v1/users/me`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+91-9876543210",
  "tenant_id": 1,
  "tenant": {
    "id": 1,
    "company_name": "My D2C Store",
    "gstin": "22AAAAA0000A1Z5"
  },
  "roles": ["admin"],
  "is_active": true,
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 8. Update User Profile

Update current user's profile information.

**Endpoint**: `PUT /api/v1/users/me`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "full_name": "John Michael Doe",
  "phone": "+91-9876543211"
}
```

**Response**: `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Michael Doe",
  "phone": "+91-9876543211",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

---

### 9. List Users (Admin Only)

List all users in the tenant.

**Endpoint**: `GET /api/v1/users`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `page` (optional, default: 1): Page number
- `page_size` (optional, default: 50): Items per page
- `is_active` (optional): Filter by active status
- `role` (optional): Filter by role (admin, manager, analyst, finance)

**Response**: `200 OK`
```json
{
  "total": 5,
  "page": 1,
  "page_size": 50,
  "users": [
    {
      "id": 1,
      "email": "user1@example.com",
      "full_name": "John Doe",
      "roles": ["admin"],
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

### 10. Create User (Admin Only)

Create a new user in the tenant.

**Endpoint**: `POST /api/v1/users`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Smith",
  "phone": "+91-9876543210",
  "roles": ["manager"]
}
```

**Response**: `201 Created`
```json
{
  "id": 2,
  "email": "newuser@example.com",
  "full_name": "Jane Smith",
  "roles": ["manager"],
  "created_at": "2025-01-15T12:00:00Z"
}
```

**Available Roles**:
- `admin`: Full access
- `manager`: Manage operations
- `analyst`: View analytics
- `finance`: View financial reports

---

## Channel Management APIs

### 11. List Channels

Get all connected sales channels.

**Endpoint**: `GET /api/v1/channels`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `is_active` (optional): Filter by active status
- `channel_type` (optional): Filter by type (shopify, woocommerce, amazon, flipkart)

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "My Shopify Store",
    "channel_type": "shopify",
    "store_url": "https://mystore.myshopify.com",
    "is_active": true,
    "is_connected": true,
    "last_sync_at": "2025-01-15T10:00:00Z",
    "last_sync_status": "success",
    "auto_sync_enabled": true,
    "sync_interval_minutes": 30,
    "created_at": "2025-01-10T09:00:00Z"
  }
]
```

---

### 12. Get Channel Details

Get details of a specific channel.

**Endpoint**: `GET /api/v1/channels/{channel_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "id": 1,
  "name": "My Shopify Store",
  "channel_type": "shopify",
  "store_url": "https://mystore.myshopify.com",
  "is_active": true,
  "is_connected": true,
  "last_sync_at": "2025-01-15T10:00:00Z",
  "last_sync_status": "success",
  "auto_sync_enabled": true,
  "sync_interval_minutes": 30,
  "webhook_enabled": true,
  "created_at": "2025-01-10T09:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

---

### 13. Connect New Channel

Connect a new sales channel.

**Endpoint**: `POST /api/v1/channels`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body - Shopify**:
```json
{
  "name": "My Shopify Store",
  "channel_type": "shopify",
  "store_url": "https://mystore.myshopify.com",
  "credentials": {
    "shop_name": "mystore",
    "access_token": "shpat_xxxxxxxxxxxxx"
  }
}
```

**Request Body - WooCommerce**:
```json
{
  "name": "My WooCommerce Store",
  "channel_type": "woocommerce",
  "store_url": "https://mystore.com",
  "credentials": {
    "store_url": "https://mystore.com",
    "consumer_key": "ck_xxxxxxxxxxxxx",
    "consumer_secret": "cs_xxxxxxxxxxxxx"
  }
}
```

**Request Body - Amazon**:
```json
{
  "name": "Amazon India",
  "channel_type": "amazon",
  "credentials": {
    "refresh_token": "Atzr|xxxxxxxxxxxxx",
    "lwa_app_id": "amzn1.application.xxxxxxxxxxxxx",
    "lwa_client_secret": "xxxxxxxxxxxxx",
    "marketplace_id": "A21TJRUUN4KGV",
    "region": "eu-west-1"
  }
}
```

**Request Body - Flipkart**:
```json
{
  "name": "Flipkart Seller",
  "channel_type": "flipkart",
  "credentials": {
    "app_id": "xxxxxxxxxxxxx",
    "app_secret": "xxxxxxxxxxxxx",
    "seller_id": "xxxxxxxxxxxxx",
    "sandbox": false
  }
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "name": "My Shopify Store",
  "channel_type": "shopify",
  "is_active": true,
  "is_connected": true,
  "last_sync_status": "pending",
  "created_at": "2025-01-15T12:00:00Z"
}
```

**Notes**:
- Credentials are automatically tested before saving
- Initial sync is triggered in the background
- Credentials are encrypted in the database

---

### 14. Update Channel Settings

Update channel configuration.

**Endpoint**: `PUT /api/v1/channels/{channel_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "name": "Updated Store Name",
  "is_active": true,
  "auto_sync_enabled": true,
  "sync_interval_minutes": 60,
  "webhook_enabled": true
}
```

**Response**: `200 OK`
```json
{
  "id": 1,
  "name": "Updated Store Name",
  "auto_sync_enabled": true,
  "sync_interval_minutes": 60,
  "updated_at": "2025-01-15T13:00:00Z"
}
```

---

### 15. Delete Channel

Deactivate a sales channel.

**Endpoint**: `DELETE /api/v1/channels/{channel_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `204 No Content`

**Notes**:
- This is a soft delete (sets `is_active = false`)
- Historical data is preserved
- Channel can be reactivated later

---

### 16. Trigger Channel Sync

Manually trigger synchronization for a channel.

**Endpoint**: `POST /api/v1/channels/{channel_id}/sync`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "channel_id": 1,
  "status": "sync_initiated",
  "message": "Channel sync has been triggered"
}
```

**Notes**:
- Sync runs in the background
- Cannot trigger if another sync is already in progress

---

### 17. Get Sync Status

Get current sync status for a channel.

**Endpoint**: `GET /api/v1/channels/{channel_id}/sync-status`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "channel_id": 1,
  "channel_name": "My Shopify Store",
  "last_sync_at": "2025-01-15T10:00:00Z",
  "last_sync_status": "success",
  "is_connected": true,
  "auto_sync_enabled": true,
  "sync_interval_minutes": 30
}
```

**Sync Status Values**:
- `pending`: Sync not yet started
- `in_progress`: Currently syncing
- `success`: Last sync completed successfully
- `failed`: Last sync failed

---

### 18. Test Channel Connection

Test if channel credentials are valid.

**Endpoint**: `POST /api/v1/channels/{channel_id}/test-connection`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "channel_id": 1,
  "is_connected": true,
  "message": "Connection successful",
  "tested_at": "2025-01-15T14:00:00Z"
}
```

---

### 19. Get Channel Statistics

Get order and product statistics for a channel.

**Endpoint**: `GET /api/v1/channels/{channel_id}/stats`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "channel_id": 1,
  "channel_name": "My Shopify Store",
  "total_orders": 1250,
  "total_revenue": 2500000.00,
  "total_products": 150,
  "is_connected": true,
  "created_at": "2025-01-10T09:00:00Z"
}
```

---

## Product Management APIs

### 20. List Products

Get all products with pagination and filters.

**Endpoint**: `GET /api/v1/products`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `page` (optional, default: 1): Page number
- `page_size` (optional, default: 50, max: 100): Items per page
- `search` (optional): Search in name, SKU, description
- `category` (optional): Filter by category
- `is_active` (optional): Filter by active status
- `is_published` (optional): Filter by published status
- `low_stock` (optional): Show only low stock products

**Response**: `200 OK`
```json
{
  "total": 150,
  "page": 1,
  "page_size": 50,
  "products": [
    {
      "id": 1,
      "name": "Premium Cotton T-Shirt",
      "sku": "TSH-001",
      "description": "Comfortable 100% cotton t-shirt",
      "category": "Apparel",
      "brand": "MyBrand",
      "cost_price": 250.00,
      "selling_price": 599.00,
      "mrp": 799.00,
      "total_stock": 150,
      "safety_stock": 20,
      "weight": 0.2,
      "tax_rate": 18.00,
      "image_url": "https://cdn.example.com/tsh-001.jpg",
      "is_active": true,
      "is_published": true,
      "tags": ["cotton", "casual", "bestseller"],
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-15T12:00:00Z"
    }
  ]
}
```

---

### 21. Get Product Details

Get details of a specific product.

**Endpoint**: `GET /api/v1/products/{product_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "id": 1,
  "name": "Premium Cotton T-Shirt",
  "sku": "TSH-001",
  "description": "Comfortable 100% cotton t-shirt",
  "category": "Apparel",
  "brand": "MyBrand",
  "cost_price": 250.00,
  "selling_price": 599.00,
  "mrp": 799.00,
  "total_stock": 150,
  "safety_stock": 20,
  "weight": 0.2,
  "hsn_code_id": 1,
  "tax_rate": 18.00,
  "image_url": "https://cdn.example.com/tsh-001.jpg",
  "is_active": true,
  "is_published": true,
  "tags": ["cotton", "casual", "bestseller"],
  "created_at": "2025-01-10T10:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

---

### 22. Create Product

Add a new product.

**Endpoint**: `POST /api/v1/products`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "name": "Premium Cotton T-Shirt",
  "sku": "TSH-001",
  "description": "Comfortable 100% cotton t-shirt",
  "category": "Apparel",
  "brand": "MyBrand",
  "cost_price": 250.00,
  "selling_price": 599.00,
  "mrp": 799.00,
  "total_stock": 150,
  "safety_stock": 20,
  "weight": 0.2,
  "hsn_code_id": 1,
  "tax_rate": 18.00,
  "image_url": "https://cdn.example.com/tsh-001.jpg",
  "tags": ["cotton", "casual"]
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "name": "Premium Cotton T-Shirt",
  "sku": "TSH-001",
  "created_at": "2025-01-15T15:00:00Z"
}
```

**Validation**:
- SKU must be unique within tenant
- Selling price should be less than or equal to MRP
- Weight in kilograms

---

### 23. Update Product

Update product details.

**Endpoint**: `PUT /api/v1/products/{product_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "name": "Premium Cotton T-Shirt - Updated",
  "selling_price": 649.00,
  "total_stock": 200,
  "is_published": true
}
```

**Response**: `200 OK`
```json
{
  "id": 1,
  "name": "Premium Cotton T-Shirt - Updated",
  "selling_price": 649.00,
  "total_stock": 200,
  "updated_at": "2025-01-15T16:00:00Z"
}
```

---

### 24. Delete Product

Soft delete a product (sets is_active = false).

**Endpoint**: `DELETE /api/v1/products/{product_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `204 No Content`

---

### 25. Adjust Product Stock

Add or remove stock quantity.

**Endpoint**: `POST /api/v1/products/{product_id}/stock-adjustment`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "adjustment": -50,
  "reason": "Sold 50 units offline"
}
```

**Response**: `200 OK`
```json
{
  "product_id": 1,
  "previous_stock": 150,
  "adjustment": -50,
  "new_stock": 100,
  "reason": "Sold 50 units offline"
}
```

**Notes**:
- Use positive numbers to add stock
- Use negative numbers to remove stock
- Cannot reduce stock below 0

---

### 26. Get Product Categories

Get list of all product categories with counts.

**Endpoint**: `GET /api/v1/products/categories/list`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "categories": [
    {
      "name": "Apparel",
      "count": 75
    },
    {
      "name": "Electronics",
      "count": 45
    },
    {
      "name": "Home & Kitchen",
      "count": 30
    }
  ]
}
```

---

### 27. Get Low Stock Alerts

Get products below safety stock level.

**Endpoint**: `GET /api/v1/products/low-stock/alert`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "count": 5,
  "products": [
    {
      "id": 1,
      "name": "Premium Cotton T-Shirt",
      "sku": "TSH-001",
      "current_stock": 15,
      "safety_stock": 20,
      "deficit": 5
    }
  ]
}
```

---

### 28. Bulk Import Products

Import multiple products at once.

**Endpoint**: `POST /api/v1/products/bulk-import`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
[
  {
    "name": "Product 1",
    "sku": "PRD-001",
    "selling_price": 499.00,
    "total_stock": 100
  },
  {
    "name": "Product 2",
    "sku": "PRD-002",
    "selling_price": 799.00,
    "total_stock": 50
  }
]
```

**Response**: `200 OK`
```json
{
  "created": 2,
  "skipped": 0,
  "errors": [],
  "total": 2
}
```

**Notes**:
- Products with existing SKUs are skipped
- Maximum 1000 products per request

---

## Order Management APIs

### 29. List Orders

Get all orders with pagination and filters.

**Endpoint**: `GET /api/v1/orders`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `page` (optional, default: 1): Page number
- `page_size` (optional, default: 50, max: 100): Items per page
- `status` (optional): Filter by status
- `payment_method` (optional): Filter by payment method (cod, prepaid)
- `date_from` (optional): Filter by order date (YYYY-MM-DD)
- `date_to` (optional): Filter by order date (YYYY-MM-DD)
- `search` (optional): Search in order number, customer name, phone, email

**Response**: `200 OK`
```json
{
  "total": 500,
  "page": 1,
  "page_size": 50,
  "orders": [
    {
      "id": 1,
      "order_number": "ORD-20250115-00001",
      "order_date": "2025-01-15T10:30:00Z",
      "status": "processing",
      "customer_name": "Rajesh Kumar",
      "customer_email": "rajesh@example.com",
      "customer_phone": "+91-9876543210",
      "payment_method": "cod",
      "payment_status": "pending",
      "subtotal": 1200.00,
      "discount_amount": 100.00,
      "shipping_charges": 50.00,
      "tax_amount": 198.00,
      "total_amount": 1348.00,
      "rto_risk_score": 45,
      "rto_risk_level": "medium",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Order Status Values**:
- `pending`: Order received
- `confirmed`: Order confirmed
- `processing`: Being prepared
- `ready_to_ship`: Ready for pickup
- `shipped`: In transit
- `out_for_delivery`: Out for delivery
- `delivered`: Successfully delivered
- `rto_initiated`: Return to origin initiated
- `rto_in_transit`: RTO in transit
- `rto_delivered`: Returned to seller
- `cancelled`: Order cancelled

---

### 30. Get Order Details

Get complete order information with items.

**Endpoint**: `GET /api/v1/orders/{order_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "id": 1,
  "order_number": "ORD-20250115-00001",
  "order_date": "2025-01-15T10:30:00Z",
  "status": "processing",
  "customer_name": "Rajesh Kumar",
  "customer_email": "rajesh@example.com",
  "customer_phone": "+91-9876543210",
  "payment_method": "cod",
  "payment_status": "pending",
  "subtotal": 1200.00,
  "discount_amount": 100.00,
  "shipping_charges": 50.00,
  "tax_amount": 198.00,
  "cgst_amount": 99.00,
  "sgst_amount": 99.00,
  "igst_amount": 0.00,
  "total_amount": 1348.00,
  "rto_risk_score": 45,
  "rto_risk_level": "medium",
  "items": [
    {
      "product_name": "Premium Cotton T-Shirt",
      "sku": "TSH-001",
      "quantity": 2,
      "unit_price": 599.00,
      "tax_amount": 198.00,
      "total_amount": 1198.00
    }
  ],
  "shipping_address": {
    "line1": "123 MG Road",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001"
  },
  "billing_address": {
    "line1": "123 MG Road",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001"
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 31. Create Order

Create a new order with automatic GST calculation and RTO prediction.

**Endpoint**: `POST /api/v1/orders`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "customer_name": "Rajesh Kumar",
  "customer_email": "rajesh@example.com",
  "customer_phone": "+91-9876543210",
  "shipping_address_line1": "123 MG Road",
  "shipping_city": "Mumbai",
  "shipping_state": "Maharashtra",
  "shipping_pincode": "400001",
  "billing_address_line1": "123 MG Road",
  "billing_city": "Mumbai",
  "billing_state": "Maharashtra",
  "billing_pincode": "400001",
  "payment_method": "cod",
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "unit_price": 599.00
    }
  ],
  "discount_amount": 100.00,
  "shipping_charges": 50.00,
  "notes": "Handle with care"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "order_number": "ORD-20250115-00001",
  "status": "pending",
  "total_amount": 1348.00,
  "rto_risk_score": 45,
  "rto_risk_level": "medium",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Notes**:
- Order number is auto-generated
- GST is calculated automatically based on billing/shipping states
- RTO prediction is performed for COD orders
- Billing address defaults to shipping if not provided

---

### 32. Update Order Status

Change order status.

**Endpoint**: `PATCH /api/v1/orders/{order_id}/status`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "new_status": "shipped"
}
```

**Response**: `200 OK`
```json
{
  "order_id": 1,
  "old_status": "processing",
  "new_status": "shipped",
  "updated_at": "2025-01-15T14:00:00Z"
}
```

**Notes**:
- Status transitions are validated
- Timestamps are automatically updated (confirmed_at, shipped_at, etc.)

---

### 33. Cancel Order

Cancel an order with reason.

**Endpoint**: `DELETE /api/v1/orders/{order_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "reason": "Customer requested cancellation"
}
```

**Response**: `204 No Content`

**Notes**:
- Cannot cancel already delivered orders
- Reason is added to order notes

---

### 34. Get Orders Analytics

Get order summary and analytics.

**Endpoint**: `GET /api/v1/orders/analytics/summary`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `date_from` (optional): Start date (YYYY-MM-DD)
- `date_to` (optional): End date (YYYY-MM-DD)

**Response**: `200 OK`
```json
{
  "total_orders": 500,
  "total_revenue": 2500000.00,
  "avg_order_value": 5000.00,
  "cod_orders": 350,
  "cod_percentage": 70.0,
  "prepaid_orders": 150,
  "delivered_orders": 450,
  "rto_orders": 25,
  "rto_rate": 5.0,
  "status_breakdown": {
    "pending": 10,
    "confirmed": 20,
    "processing": 30,
    "shipped": 50,
    "delivered": 450,
    "cancelled": 15,
    "rto_delivered": 25
  }
}
```

---

## Analytics APIs

### 35. Get Dashboard Analytics

Get comprehensive dashboard metrics.

**Endpoint**: `GET /api/v1/analytics/dashboard`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `period` (optional, default: 30): Number of days (7, 30, 90)

**Response**: `200 OK`
```json
{
  "period_days": 30,
  "orders": {
    "total": 500,
    "growth_percentage": 15.5,
    "trend": "up"
  },
  "revenue": {
    "total": 2500000.00,
    "growth_percentage": 20.3,
    "trend": "up"
  },
  "avg_order_value": {
    "value": 5000.00,
    "growth_percentage": 4.2,
    "trend": "up"
  },
  "rto_rate": {
    "value": 5.0,
    "growth_percentage": -10.5,
    "trend": "down"
  },
  "top_products": [
    {
      "id": 1,
      "name": "Premium Cotton T-Shirt",
      "units_sold": 200,
      "revenue": 119800.00
    }
  ],
  "channel_wise_revenue": [
    {
      "channel_name": "Shopify",
      "revenue": 1500000.00,
      "orders": 300
    },
    {
      "channel_name": "Amazon",
      "revenue": 800000.00,
      "orders": 150
    }
  ]
}
```

---

### 36. Get RTO Analytics

Get detailed RTO (Return to Origin) analytics.

**Endpoint**: `GET /api/v1/analytics/rto`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `date_from` (optional): Start date
- `date_to` (optional): End date

**Response**: `200 OK`
```json
{
  "total_orders": 500,
  "rto_orders": 25,
  "rto_rate": 5.0,
  "rto_by_pincode": [
    {
      "pincode": "400001",
      "rto_count": 5,
      "rto_rate": 10.0
    }
  ],
  "rto_by_channel": [
    {
      "channel_name": "Shopify",
      "rto_count": 15,
      "rto_rate": 5.0
    }
  ],
  "high_risk_pincodes": [
    {
      "pincode": "400001",
      "risk_score": 75,
      "risk_level": "high"
    }
  ]
}
```

---

### 37. Get Demand Forecast

Get AI-powered demand forecasting for products.

**Endpoint**: `GET /api/v1/analytics/demand-forecast`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `product_id` (optional): Specific product
- `category` (optional): Product category
- `days` (optional, default: 30): Forecast period (30, 60, 90)

**Response**: `200 OK`
```json
{
  "product_id": 1,
  "product_name": "Premium Cotton T-Shirt",
  "forecast_period_days": 30,
  "forecasts": [
    {
      "date": "2025-01-16",
      "predicted_demand": 15,
      "lower_bound": 12,
      "upper_bound": 18
    }
  ],
  "stockout_alerts": [
    {
      "date": "2025-01-25",
      "severity": "high",
      "message": "Stock will run out by this date"
    }
  ],
  "reorder_recommendation": {
    "quantity": 200,
    "by_date": "2025-01-20"
  }
}
```

---

## Subscription & Billing APIs

### 38. Get Current Subscription

Get current subscription details.

**Endpoint**: `GET /api/v1/subscriptions/current`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "id": 1,
  "plan_name": "Professional",
  "status": "active",
  "current_period_start": "2025-01-01T00:00:00Z",
  "current_period_end": "2025-02-01T00:00:00Z",
  "amount": 2999.00,
  "currency": "INR",
  "auto_renew": true,
  "features": {
    "max_channels": 5,
    "max_orders_per_month": 10000,
    "ml_predictions": true,
    "gst_reports": true,
    "api_access": true
  },
  "usage": {
    "channels_used": 3,
    "orders_this_month": 5000,
    "usage_percentage": 50.0
  }
}
```

---

### 39. List Available Plans

Get all available subscription plans.

**Endpoint**: `GET /api/v1/subscriptions/plans`

**Response**: `200 OK`
```json
[
  {
    "id": "plan_basic",
    "name": "Basic",
    "price": 999.00,
    "currency": "INR",
    "interval": "month",
    "features": {
      "max_channels": 2,
      "max_orders_per_month": 1000,
      "ml_predictions": false,
      "gst_reports": true,
      "api_access": false
    }
  },
  {
    "id": "plan_professional",
    "name": "Professional",
    "price": 2999.00,
    "currency": "INR",
    "interval": "month",
    "features": {
      "max_channels": 5,
      "max_orders_per_month": 10000,
      "ml_predictions": true,
      "gst_reports": true,
      "api_access": true
    }
  },
  {
    "id": "plan_enterprise",
    "name": "Enterprise",
    "price": 9999.00,
    "currency": "INR",
    "interval": "month",
    "features": {
      "max_channels": -1,
      "max_orders_per_month": -1,
      "ml_predictions": true,
      "gst_reports": true,
      "api_access": true,
      "dedicated_support": true
    }
  }
]
```

---

### 40. Create Subscription

Create a new subscription.

**Endpoint**: `POST /api/v1/subscriptions`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "plan_id": "plan_professional"
}
```

**Response**: `201 Created`
```json
{
  "subscription_id": "sub_xxxxxxxxxxxxx",
  "payment_link": "https://rzp.io/i/xxxxxxxxxxxxx",
  "status": "created"
}
```

**Notes**:
- Redirects to Razorpay for payment
- Webhook will update status after payment

---

### 41. Cancel Subscription

Cancel current subscription.

**Endpoint**: `DELETE /api/v1/subscriptions/current`

**Headers**: `Authorization: Bearer <access_token>`

**Response**: `200 OK`
```json
{
  "message": "Subscription cancelled. Access until 2025-02-01",
  "cancelled_at": "2025-01-15T15:00:00Z",
  "access_until": "2025-02-01T00:00:00Z"
}
```

---

## Webhooks

### Razorpay Webhooks

**Endpoint**: `POST /api/v1/webhooks/razorpay`

**Events**:
- `subscription.activated`: Subscription activated
- `subscription.charged`: Payment successful
- `subscription.cancelled`: Subscription cancelled
- `subscription.paused`: Subscription paused

**Webhook Signature Verification**: Included

---

### Channel Webhooks (Future)

Webhooks for real-time order updates from channels.

**Planned Endpoints**:
- `/api/v1/webhooks/shopify`
- `/api/v1/webhooks/woocommerce`

---

## Error Codes

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Request successful, no content returned |
| 400 | Bad Request - Invalid request format or parameters |
| 401 | Unauthorized - Authentication required or failed |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists (e.g., duplicate SKU) |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

### Common Error Response Format

```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "fields": {
    "email": ["Invalid email format"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

### Custom Error Codes

| Code | Description |
|------|-------------|
| AUTH_FAILED | Authentication failed |
| TOKEN_EXPIRED | Access token expired |
| INVALID_CREDENTIALS | Invalid username or password |
| ACCOUNT_LOCKED | Account locked due to failed attempts |
| INSUFFICIENT_PERMISSIONS | User lacks required permissions |
| RESOURCE_NOT_FOUND | Requested resource not found |
| DUPLICATE_RESOURCE | Resource already exists |
| VALIDATION_ERROR | Request validation failed |
| CHANNEL_CONNECTION_ERROR | Failed to connect to channel |
| SYNC_IN_PROGRESS | Sync already in progress |
| SUBSCRIPTION_INACTIVE | Subscription is not active |
| USAGE_LIMIT_EXCEEDED | Usage limit exceeded for plan |
| RATE_LIMIT_EXCEEDED | API rate limit exceeded |

---

## Postman Collection

A Postman collection with all endpoints and examples is available:

**Download**: [D2C-Analytics-Platform.postman_collection.json](./D2C-Analytics-Platform.postman_collection.json)

### Using the Collection

1. Import the collection into Postman
2. Set up environment variables:
   - `base_url`: Your API base URL
   - `access_token`: Your access token (obtained from login)
3. Run the "Login" request first to get tokens
4. All subsequent requests will use the token automatically

---

## Interactive API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Both interfaces allow you to:
- Browse all available endpoints
- See request/response schemas
- Test API calls directly from the browser
- View detailed parameter descriptions

---

## SDK & Client Libraries

### Python SDK (Coming Soon)

```python
from ciruss import CirussClient

client = CirussClient(api_key="your_api_key")

# List orders
orders = client.orders.list(status="pending", page=1)

# Create product
product = client.products.create(
    name="T-Shirt",
    sku="TSH-001",
    price=599.00
)
```

### JavaScript SDK (Coming Soon)

```javascript
import { CirussClient } from '@ciruss/sdk';

const client = new CirussClient({ apiKey: 'your_api_key' });

// List orders
const orders = await client.orders.list({ status: 'pending' });

// Create product
const product = await client.products.create({
  name: 'T-Shirt',
  sku: 'TSH-001',
  price: 599.00
});
```

---

## Support

For API support:
- **Email**: api-support@ciruss.io
- **Documentation**: https://docs.ciruss.io
- **Status Page**: https://status.ciruss.io

---

**Built with ❤️ for Indian D2C Brands**

*Last Updated: 2025-11-27*
*API Version: 3.0*
