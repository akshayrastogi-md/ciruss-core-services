# D2C Analytics Platform - Frontend API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Analytics APIs](#analytics-apis)
4. [Reports APIs](#reports-apis)
5. [Inventory APIs](#inventory-apis)
6. [Marketing APIs](#marketing-apis)
7. [Subscription APIs](#subscription-apis)
8. [User Management APIs](#user-management-apis)
9. [Channel & Order APIs](#channel--order-apis)
10. [Webhooks](#webhooks)
11. [Data Models & Calculations](#data-models--calculations)

---

## Overview

**Base URL**: `/api/v1`

All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

**Response Format**: All responses are in JSON format
**Date Format**: ISO 8601 (e.g., "2024-01-15")
**Currency**: All amounts in INR (₹)
**Timezone**: Asia/Kolkata (IST)

---

## Authentication

### 1. Register User
**POST** `/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "phone": "+919876543210",
  "company_name": "ABC Fashion",
  "gstin": "29ABCDE1234F1Z5"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### 2. Login
**POST** `/auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response**: Same as register

### 3. Refresh Token
**POST** `/auth/refresh`

**Headers**:
```
Authorization: Bearer <refresh_token>
```

---

## Analytics APIs

### 1. Dashboard Overview
**GET** `/analytics/dashboard?start_date=2024-01-01&end_date=2024-01-31`

**Query Parameters**:
- `start_date` (optional): Start date (defaults to 30 days ago)
- `end_date` (optional): End date (defaults to today)

**Response**:
```json
{
  "total_revenue": 1250000.50,
  "total_orders": 543,
  "average_order_value": 2302.39,
  "profit_margin": 23.5,
  "rto_rate": 12.3,
  "cod_percentage": 67.8,
  "active_skus": 145,
  "marketing_spend": 45000.00,
  "roas": 4.5,
  "revenue_change": 15.2,
  "orders_change": 8.7,
  "aov_change": 5.3
}
```

**Calculated Metrics**:
- `total_revenue`: Sum of all order amounts
- `average_order_value`: Total revenue / Total orders
- `profit_margin`: (Profit / Revenue) × 100
- `rto_rate`: (RTO orders / Total orders) × 100
- `cod_percentage`: (COD orders / Total orders) × 100
- `roas`: Marketing revenue / Marketing spend
- `*_change`: ((Current - Previous) / Previous) × 100

---

### 2. Revenue Trend
**GET** `/analytics/revenue-trend?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "date": "2024-01-01",
    "revenue": 45000.00,
    "orders": 23,
    "forecast": 48000.00
  },
  {
    "date": "2024-01-02",
    "revenue": 52000.00,
    "orders": 28,
    "forecast": 50000.00
  }
]
```

**Data Points**:
- Daily revenue and order count
- Optional forecast overlay (from ML models)

---

### 3. Channel Performance
**GET** `/analytics/channel-performance?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "channel_id": 1,
    "channel_name": "Shopify Store",
    "channel_type": "shopify",
    "revenue": 450000.00,
    "orders": 234,
    "percentage": 36.5
  },
  {
    "channel_id": 2,
    "channel_name": "Amazon India",
    "channel_type": "amazon",
    "revenue": 380000.00,
    "orders": 189,
    "percentage": 30.8
  }
]
```

**Calculations**:
- `percentage`: (Channel revenue / Total revenue) × 100
- Sorted by revenue (highest to lowest)

---

### 4. Top Products
**GET** `/analytics/top-products?start_date=2024-01-01&end_date=2024-01-31&limit=10`

**Query Parameters**:
- `limit`: Number of products to return (1-100, default: 10)

**Response**:
```json
[
  {
    "product_id": 123,
    "product_name": "Premium Cotton T-Shirt",
    "sku": "TSHIRT-001",
    "revenue": 125000.00,
    "quantity_sold": 543
  }
]
```

---

### 5. State-wise Revenue
**GET** `/analytics/state-revenue?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "state": "Maharashtra",
    "revenue": 320000.00,
    "orders": 156
  },
  {
    "state": "Karnataka",
    "revenue": 280000.00,
    "orders": 142
  }
]
```

---

### 6. Payment Method Distribution
**GET** `/analytics/payment-method-distribution?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "method": "COD",
    "count": 368,
    "percentage": 67.8
  },
  {
    "method": "Prepaid",
    "count": 175,
    "percentage": 32.2
  }
]
```

---

### 7. Order Status Distribution
**GET** `/analytics/order-status-distribution?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "status": "delivered",
    "count": 423,
    "percentage": 77.9
  },
  {
    "status": "rto",
    "count": 67,
    "percentage": 12.3
  },
  {
    "status": "in_transit",
    "count": 38,
    "percentage": 7.0
  },
  {
    "status": "cancelled",
    "count": 15,
    "percentage": 2.8
  }
]
```

---

### 8. Daily Metrics
**GET** `/analytics/daily-metrics?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "date": "2024-01-01",
    "revenue": 45000.00,
    "orders": 23,
    "confirmed_orders": 20,
    "shipped_orders": 18,
    "delivered_orders": 22,
    "cancelled_orders": 1,
    "rto_orders": 2,
    "cod_orders": 16,
    "prepaid_orders": 7,
    "cod_percentage": 69.6,
    "rto_rate": 8.7,
    "rto_cost": 1200.00,
    "new_customers": 12,
    "returning_customers": 11,
    "repeat_purchase_rate": 47.8,
    "cogs": 27000.00,
    "profit": 18000.00,
    "profit_margin": 40.0,
    "marketing_spend": 5000.00,
    "marketing_revenue": 22500.00,
    "marketing_roas": 4.5,
    "cac": 416.67,
    "inventory_value": 2500000.00,
    "stockouts": 3
  }
]
```

**Metric Definitions**:
- `rto_rate`: (RTO orders / Total orders) × 100
- `cod_percentage`: (COD orders / Total orders) × 100
- `repeat_purchase_rate`: (Returning customers / Total customers) × 100
- `profit_margin`: (Profit / Revenue) × 100
- `marketing_roas`: Marketing revenue / Marketing spend
- `cac`: Marketing spend / New customers

---

### 9. Pin Code Metrics
**GET** `/analytics/pincode-metrics?limit=100&offset=0&risk_level=High&state=Maharashtra`

**Query Parameters**:
- `limit`: Number of records (1-1000, default: 100)
- `offset`: Pagination offset (default: 0)
- `risk_level`: Filter by risk level (Low/Medium/High)
- `state`: Filter by state

**Response**:
```json
[
  {
    "pincode": "400001",
    "city": "Mumbai",
    "state": "Maharashtra",
    "tier": "1",
    "total_orders": 156,
    "delivered_orders": 132,
    "rto_orders": 24,
    "rto_rate": 15.4,
    "delivery_success_rate": 84.6,
    "risk_score": 62,
    "risk_level": "High",
    "cod_orders": 98,
    "cod_percentage": 62.8,
    "avg_order_value": 2345.00,
    "avg_delivery_days": 3.2,
    "last_updated": "2024-01-15T10:30:00Z"
  }
]
```

**Risk Score Calculation**:
- Range: 0-100
- Based on: Historical RTO rate, delivery success rate, COD performance
- Levels: Low (0-39), Medium (40-69), High (70-100)

---

### 10. COD/RTO Analytics
**GET** `/analytics/cod-rto-analytics?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
{
  "overall_rto_rate": 12.3,
  "cod_rto_rate": 15.6,
  "prepaid_rto_rate": 6.2,
  "total_rto_cost": 45000.00,
  "channel_breakdown": [
    {
      "channel": "Shopify",
      "total_orders": 234,
      "rto_orders": 28,
      "rto_rate": 12.0
    }
  ],
  "courier_breakdown": [
    {
      "courier": "Delhivery",
      "total_orders": 156,
      "rto_orders": 18,
      "rto_rate": 11.5
    }
  ],
  "category_breakdown": [
    {
      "category": "Fashion",
      "total_orders": 345,
      "rto_orders": 52,
      "rto_rate": 15.1
    }
  ],
  "high_risk_pincodes": 23,
  "medium_risk_pincodes": 45,
  "low_risk_pincodes": 128,
  "total_ndr": 34,
  "ndr_resolved": 28,
  "ndr_pending": 6,
  "ndr_resolution_rate": 82.4
}
```

**Calculations**:
- `overall_rto_rate`: (Total RTO orders / Total orders) × 100
- `cod_rto_rate`: (COD RTO orders / Total COD orders) × 100
- `prepaid_rto_rate`: (Prepaid RTO orders / Total prepaid orders) × 100
- `ndr_resolution_rate`: (NDR resolved / Total NDR) × 100

---

### 11. Inventory Analytics
**GET** `/analytics/inventory-analytics`

**Response**:
```json
{
  "total_inventory_value": 2500000.00,
  "total_skus": 245,
  "active_skus": 218,
  "avg_doi": 32.5,
  "inventory_turnover_ratio": 4.2,
  "annual_holding_cost_percentage": 25.0,
  "estimated_holding_cost": 625000.00,
  "critical_stockouts": 5,
  "high_stockouts": 12,
  "medium_stockouts": 23,
  "dead_stock_items": 8,
  "very_slow_moving": 15,
  "slow_moving": 28,
  "dead_stock_value": 125000.00
}
```

**Metric Definitions**:
- `avg_doi`: Average Days of Inventory = 365 / Inventory turnover ratio
- `inventory_turnover_ratio`: COGS / Average inventory value
- `estimated_holding_cost`: Inventory value × Holding cost %
- **Stockout Severity**: Critical (<7 days), High (<14 days), Medium (<30 days)
- **Dead Stock**: Dead (90+ days), Very Slow (60-90 days), Slow (30-60 days)

---

## Reports APIs

### 1. Generate Report
**POST** `/reports/generate`

**Request Body**:
```json
{
  "report_type": "sales",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "format": "excel",
  "filters": {
    "channel_id": 1,
    "status": "delivered"
  }
}
```

**Report Types**:
- `sales`: Sales report with order details
- `product_performance`: Product-wise performance
- `gst`: Monthly GST report (IGST, CGST, SGST, TCS)
- `pl_by_channel`: Profit & Loss by channel
- `rto_analysis`: RTO analysis with pin code breakdown
- `inventory`: Inventory report with valuations
- `forecast`: Demand forecast report
- `marketing_performance`: Marketing campaign performance

**Export Formats**:
- `excel`: Multi-sheet Excel workbook
- `csv`: CSV file
- `pdf`: Professional PDF report

**Response**:
```json
{
  "id": 123,
  "report_type": "sales",
  "status": "pending",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "format": "excel",
  "file_url": null,
  "file_size": null,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": null
}
```

---

### 2. List Reports
**GET** `/reports/?report_type=sales&status=completed&limit=50&offset=0`

**Response**:
```json
[
  {
    "id": 123,
    "report_type": "sales",
    "status": "completed",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "format": "excel",
    "file_url": "https://s3.amazonaws.com/reports/123.xlsx",
    "file_size": 245678,
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:35:00Z"
  }
]
```

---

### 3. Schedule Report
**POST** `/reports/schedules`

**Request Body**:
```json
{
  "report_type": "sales",
  "frequency": "daily",
  "format": "excel",
  "recipients": ["user@example.com", "manager@example.com"],
  "filters": {
    "channel_id": 1
  },
  "is_active": true
}
```

**Frequencies**:
- `daily`: Generated daily at 9 AM
- `weekly`: Generated weekly on Monday at 9 AM
- `monthly`: Generated on 1st of every month at 9 AM

**Response**:
```json
{
  "id": 45,
  "report_type": "sales",
  "frequency": "daily",
  "format": "excel",
  "recipients": ["user@example.com"],
  "is_active": true,
  "last_run_at": "2024-01-15T09:00:00Z",
  "next_run_at": "2024-01-16T09:00:00Z",
  "created_at": "2024-01-10T10:30:00Z"
}
```

---

## Inventory APIs

### 1. Inventory Snapshots
**GET** `/inventory/snapshots?limit=100&offset=0`

**Response**:
```json
[
  {
    "id": 123,
    "product_variant_id": 45,
    "product_name": "Cotton T-Shirt - Blue",
    "sku": "TSHIRT-BLUE-M",
    "quantity": 145,
    "unit_cost": 250.00,
    "total_value": 36250.00,
    "snapshot_date": "2024-01-15T04:00:00Z"
  }
]
```

---

### 2. Stock Alerts
**GET** `/inventory/stock-alerts?is_resolved=false&severity=Critical`

**Query Parameters**:
- `is_resolved`: Filter by resolution status (true/false)
- `severity`: Filter by severity (Critical/High/Medium)

**Response**:
```json
[
  {
    "id": 67,
    "product_variant_id": 45,
    "product_name": "Cotton T-Shirt - Blue",
    "sku": "TSHIRT-BLUE-M",
    "alert_type": "stockout_prediction",
    "current_stock": 23,
    "predicted_stockout_date": "2024-01-20",
    "days_until_stockout": 5,
    "recommended_reorder_qty": 150,
    "severity": "Critical",
    "is_resolved": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Severity Levels**:
- **Critical**: Stockout in <7 days
- **High**: Stockout in <14 days
- **Medium**: Stockout in <30 days

---

### 3. SKU Profitability
**GET** `/inventory/profitability?limit=50&offset=0`

**Response**:
```json
[
  {
    "product_id": 12,
    "product_name": "Premium Jeans",
    "sku": "JEANS-001",
    "revenue": 125000.00,
    "cogs": 62500.00,
    "platform_fees": 2500.00,
    "payment_gateway_fees": 2500.00,
    "shipping_cost": 15000.00,
    "rto_cost": 3000.00,
    "marketing_cost": 12500.00,
    "net_profit": 27000.00,
    "profit_margin": 21.6,
    "units_sold": 250
  }
]
```

**Profit Calculation**:
```
Net Profit = Revenue - (COGS + Platform Fees + Payment Gateway Fees + Shipping + RTO Costs + Marketing)
Profit Margin = (Net Profit / Revenue) × 100
```

**Fee Assumptions** (configurable):
- Platform fees: 2% of revenue
- Payment gateway: 2% of revenue
- Shipping: ₹50 per unit (average)
- Marketing: 10% of revenue (allocated)

---

### 4. Dead Stock Analysis
**GET** `/inventory/dead-stock?limit=100&offset=0`

**Response**:
```json
[
  {
    "product_variant_id": 78,
    "product_name": "Winter Jacket - Red",
    "sku": "JACKET-RED-L",
    "current_stock": 45,
    "days_since_last_sale": 95,
    "stock_value": 67500.00,
    "classification": "Dead",
    "aging_bracket": "90+",
    "recommended_markdown": 40.0,
    "recommended_clearance_price": 900.00
  }
]
```

**Classifications**:
- **Dead**: No sales in 90+ days (40-50% markdown)
- **Very Slow**: No sales in 60-90 days (30-40% markdown)
- **Slow Moving**: No sales in 30-60 days (20-30% markdown)

**Aging Brackets**:
- 0-30 days
- 30-60 days
- 60-90 days
- 90-180 days
- 180+ days

---

### 5. Inventory Turnover
**GET** `/inventory/turnover-analysis?limit=50&offset=0`

**Response**:
```json
[
  {
    "product_variant_id": 45,
    "product_name": "Cotton T-Shirt",
    "sku": "TSHIRT-001",
    "avg_inventory_value": 50000.00,
    "cogs": 200000.00,
    "inventory_turnover_ratio": 4.0,
    "days_of_inventory": 91.25,
    "performance_rating": "Good"
  }
]
```

**Performance Ratings**:
- **Excellent**: Turnover ratio ≥ 8
- **Good**: Turnover ratio ≥ 4
- **Average**: Turnover ratio ≥ 2
- **Poor**: Turnover ratio < 2

**Calculations**:
```
Inventory Turnover Ratio = Annual COGS / Average Inventory Value
Days of Inventory = 365 / Inventory Turnover Ratio
```

---

## Marketing APIs

### 1. List Campaigns
**GET** `/marketing/campaigns?platform=facebook&status=active&limit=100`

**Query Parameters**:
- `platform`: Filter by platform (facebook/google)
- `status`: Filter by status (active/paused/ended)

**Response**:
```json
[
  {
    "id": 123,
    "platform": "facebook",
    "campaign_id": "FB_123456789",
    "campaign_name": "Summer Sale 2024",
    "status": "active",
    "objective": "conversions",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

---

### 2. Ad Spend Data
**GET** `/marketing/ad-spend?start_date=2024-01-01&end_date=2024-01-31&platform=facebook`

**Response**:
```json
[
  {
    "id": 456,
    "campaign_id": 123,
    "campaign_name": "Summer Sale 2024",
    "platform": "facebook",
    "date": "2024-01-15",
    "spend": 5000.00,
    "impressions": 125000,
    "clicks": 2500,
    "conversions": 125,
    "revenue": 25000.00,
    "roas": 5.0,
    "cpc": 2.0,
    "ctr": 2.0,
    "cpa": 40.0
  }
]
```

**Metric Calculations**:
- `roas`: Revenue / Spend
- `cpc`: Spend / Clicks
- `ctr`: (Clicks / Impressions) × 100
- `cpa`: Spend / Conversions

---

### 3. Campaign Performance
**GET** `/marketing/campaign-performance?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
[
  {
    "campaign_id": 123,
    "campaign_name": "Summer Sale 2024",
    "platform": "facebook",
    "total_spend": 150000.00,
    "total_impressions": 3750000,
    "total_clicks": 75000,
    "total_conversions": 3750,
    "total_revenue": 750000.00,
    "roas": 5.0,
    "avg_cpc": 2.0,
    "avg_ctr": 2.0,
    "avg_cpa": 40.0
  }
]
```

---

### 4. CAC & LTV Metrics
**GET** `/marketing/cac-ltv?start_date=2024-01-01&end_date=2024-01-31`

**Response**:
```json
{
  "total_customers": 1250,
  "new_customers": 856,
  "acquisition_cost": 150000.00,
  "cac": 175.23,
  "avg_ltv": 8500.00,
  "ltv_cac_ratio": 48.5,
  "payback_period_days": 45
}
```

**Calculations**:
- `cac`: Total marketing spend / New customers
- `avg_ltv`: Average customer lifetime value (6-month revenue × 3)
- `ltv_cac_ratio`: Average LTV / CAC
- `payback_period_days`: Days to recover CAC based on average revenue

**Healthy Ratios**:
- LTV/CAC ratio > 3 is good
- LTV/CAC ratio > 5 is excellent
- Payback period < 90 days is ideal

---

## Subscription APIs

### 1. List Plans
**GET** `/subscriptions/plans`

**Response**:
```json
[
  {
    "id": 1,
    "name": "Trial",
    "slug": "trial",
    "price": 0,
    "billing_period": "monthly",
    "max_channels": 1,
    "max_orders": 50,
    "features": {
      "analytics": true,
      "reports": false,
      "ml_predictions": false,
      "api_access": false
    },
    "is_active": true
  },
  {
    "id": 2,
    "name": "Starter",
    "slug": "starter",
    "price": 2999,
    "billing_period": "monthly",
    "max_channels": 2,
    "max_orders": 500,
    "features": {
      "analytics": true,
      "reports": true,
      "ml_predictions": false,
      "api_access": false
    },
    "is_active": true
  },
  {
    "id": 3,
    "name": "Growth",
    "slug": "growth",
    "price": 7999,
    "billing_period": "monthly",
    "max_channels": 5,
    "max_orders": 2000,
    "features": {
      "analytics": true,
      "reports": true,
      "ml_predictions": true,
      "api_access": true
    },
    "is_active": true
  },
  {
    "id": 4,
    "name": "Professional",
    "slug": "professional",
    "price": 19999,
    "billing_period": "monthly",
    "max_channels": null,
    "max_orders": null,
    "features": {
      "analytics": true,
      "reports": true,
      "ml_predictions": true,
      "api_access": true,
      "dedicated_support": true
    },
    "is_active": true
  }
]
```

---

### 2. Current Subscription
**GET** `/subscriptions/current`

**Response**:
```json
{
  "id": 45,
  "tenant_id": 12,
  "plan_id": 3,
  "plan_name": "Growth",
  "razorpay_subscription_id": "sub_JKL123456789",
  "status": "active",
  "current_period_start": "2024-01-01T00:00:00Z",
  "current_period_end": "2024-01-31T23:59:59Z",
  "cancel_at_period_end": false,
  "created_at": "2024-01-01T10:00:00Z"
}
```

**Status Values**:
- `trialing`: Free trial period
- `active`: Active subscription
- `paused`: Temporarily paused
- `cancelled`: Cancelled
- `pending`: Payment pending

---

### 3. Usage Metrics
**GET** `/subscriptions/usage`

**Response**:
```json
{
  "plan_name": "Growth",
  "max_channels": 5,
  "current_channels": 3,
  "max_orders": 2000,
  "current_orders": 1645,
  "usage_percentage": 82.25,
  "is_overaged": false,
  "overage_amount": 0
}
```

**Usage Alerts**:
- Warning at 80% usage
- Critical at 90% usage
- Overage charges after 100% (if applicable)

---

### 4. Invoices
**GET** `/subscriptions/invoices?limit=50&offset=0`

**Response**:
```json
[
  {
    "id": 123,
    "subscription_id": 45,
    "invoice_number": "INV-20240115-45",
    "razorpay_invoice_id": "inv_ABC123",
    "amount": 7999.00,
    "tax": 1439.82,
    "total": 9438.82,
    "status": "paid",
    "invoice_date": "2024-01-15T00:00:00Z",
    "due_date": "2024-01-20T00:00:00Z",
    "paid_at": "2024-01-15T10:30:00Z",
    "invoice_url": "https://razorpay.com/invoices/ABC123.pdf"
  }
]
```

---

## User Management APIs

### 1. List Users
**GET** `/users/?limit=50&offset=0`

**Response**:
```json
[
  {
    "id": 12,
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+919876543210",
    "is_active": true,
    "is_verified": true,
    "created_at": "2024-01-01T10:00:00Z",
    "roles": ["Admin", "Manager"]
  }
]
```

---

### 2. Available Roles
**GET** `/users/roles/`

**Response**:
```json
[
  {
    "id": 1,
    "name": "Admin",
    "slug": "admin",
    "description": "Full system access"
  },
  {
    "id": 2,
    "name": "Manager",
    "slug": "manager",
    "description": "Manage operations and users"
  },
  {
    "id": 3,
    "name": "Analyst",
    "slug": "analyst",
    "description": "View analytics and reports"
  },
  {
    "id": 4,
    "name": "Finance",
    "slug": "finance",
    "description": "Manage billing and GST"
  }
]
```

**Role Permissions**:

| Feature | Admin | Manager | Analyst | Finance |
|---------|-------|---------|---------|---------|
| View Analytics | ✅ | ✅ | ✅ | ✅ |
| Manage Orders | ✅ | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ✅ | ❌ | ❌ |
| Manage Channels | ✅ | ✅ | ❌ | ❌ |
| View Reports | ✅ | ✅ | ✅ | ✅ |
| Manage Subscriptions | ✅ | ❌ | ❌ | ✅ |
| GST & Invoices | ✅ | ✅ | ❌ | ✅ |
| API Keys | ✅ | ✅ | ❌ | ❌ |

---

### 3. API Keys
**GET** `/users/api-keys/`

**Response**:
```json
[
  {
    "id": 5,
    "name": "Mobile App Production",
    "key_prefix": "d2c_live_abc",
    "scopes": ["read", "write"],
    "is_active": true,
    "last_used_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": null
  }
]
```

**Available Scopes**:
- `read`: Read-only access
- `write`: Create and update operations
- `full`: Full access including delete

---

## Channel & Order APIs

### 1. List Channels
**GET** `/channels/?limit=50&offset=0`

**Response**:
```json
[
  {
    "id": 1,
    "name": "Shopify Store",
    "channel_type": "shopify",
    "status": "connected",
    "last_sync_at": "2024-01-15T10:00:00Z",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

**Channel Types**:
- `shopify`: Shopify store
- `woocommerce`: WooCommerce website
- `amazon`: Amazon India
- `flipkart`: Flipkart Seller

---

### 2. List Orders
**GET** `/orders/?channel_id=1&status=delivered&start_date=2024-01-01&limit=50`

**Response**:
```json
[
  {
    "id": 123,
    "order_number": "ORD-2024-001",
    "channel_id": 1,
    "customer_name": "Ramesh Kumar",
    "customer_email": "ramesh@example.com",
    "customer_phone": "+919876543210",
    "total_amount": 2500.00,
    "payment_method": "COD",
    "status": "delivered",
    "shipping_pincode": "400001",
    "shipping_state": "Maharashtra",
    "created_at": "2024-01-10T14:30:00Z",
    "updated_at": "2024-01-13T16:45:00Z"
  }
]
```

**Order Statuses**:
- `pending`: Order placed
- `confirmed`: Order confirmed
- `shipped`: Order shipped
- `out_for_delivery`: Out for delivery
- `delivered`: Successfully delivered
- `cancelled`: Order cancelled
- `rto`: Returned to origin

---

## Webhooks

### Webhook Events

The platform sends webhook notifications for real-time updates:

#### 1. Razorpay Events
**POST** `/webhooks/razorpay`

**Events**:
- `subscription.activated`
- `subscription.charged`
- `subscription.cancelled`
- `subscription.paused`
- `subscription.resumed`

---

#### 2. Shiprocket Events
**POST** `/webhooks/shiprocket`

**Events**:
- `PICKUP_SCHEDULED`
- `PICKED_UP`
- `IN_TRANSIT`
- `OUT_FOR_DELIVERY`
- `DELIVERED`
- `RTO_INITIATED`
- `CANCELLED`

---

#### 3. Channel Webhooks
**POST** `/webhooks/shopify`
**POST** `/webhooks/woocommerce`

**Events**:
- Order created
- Order updated
- Product created
- Product updated

---

## Data Models & Calculations

### 1. Key Performance Indicators (KPIs)

#### Revenue Metrics
```
GMV (Gross Merchandise Value) = Sum of all order amounts
Net Revenue = GMV - Cancellations - Returns
Average Order Value (AOV) = Total Revenue / Number of Orders
Revenue Growth = ((Current Period - Previous Period) / Previous Period) × 100
```

#### Order Metrics
```
Order Count = Total number of orders
Conversion Rate = (Orders / Website Visitors) × 100
Repeat Purchase Rate = (Returning Customers / Total Customers) × 100
```

#### Profitability Metrics
```
Gross Profit = Revenue - COGS
Gross Margin = (Gross Profit / Revenue) × 100
Net Profit = Revenue - (COGS + Operating Expenses + Marketing + Shipping + RTO Costs)
Net Margin = (Net Profit / Revenue) × 100

Operating Expenses Breakdown:
- Platform fees (Shopify, Amazon, etc.)
- Payment gateway fees
- Shipping costs
- RTO costs
- Marketing costs
- Holding costs
```

#### RTO Metrics
```
RTO Rate = (RTO Orders / Total Orders) × 100
RTO Cost = Number of RTO Orders × (Shipping Cost + Handling Cost)
COD RTO Rate = (COD RTO Orders / Total COD Orders) × 100
Prepaid RTO Rate = (Prepaid RTO Orders / Total Prepaid Orders) × 100
```

#### Marketing Metrics
```
ROAS (Return on Ad Spend) = Revenue from Ads / Ad Spend
CAC (Customer Acquisition Cost) = Total Marketing Spend / New Customers
LTV (Lifetime Value) = Average Order Value × Purchase Frequency × Customer Lifespan
LTV/CAC Ratio = LTV / CAC
Payback Period = CAC / (Average Monthly Revenue per Customer)
```

#### Inventory Metrics
```
Inventory Turnover = COGS / Average Inventory Value
Days of Inventory (DOI) = 365 / Inventory Turnover Ratio
Stock Coverage = Current Stock / Average Daily Demand
Stockout Rate = (Stockout Days / Total Days) × 100
Dead Stock % = (Dead Stock Value / Total Inventory Value) × 100
```

---

### 2. ML Predictions

#### RTO Prediction
**Input Features**:
- Order value
- Payment method (COD/Prepaid)
- Pin code historical RTO rate
- Product category
- Customer type (new/returning)
- Day of week
- Courier partner
- Delivery tier (1/2/3)

**Output**:
- RTO Probability: 0.0 to 1.0 (0% to 100%)
- Risk Score: 0 to 100
- Risk Level: Low/Medium/High
- Recommendation: Accept/Review/Reject

**Model Performance**:
- Target Accuracy: >75%
- Updated: Weekly (Sunday 2 AM)

---

#### Demand Forecasting
**Input Features**:
- Historical sales (6-24 months)
- Seasonality patterns
- Indian festivals & holidays
- Wedding seasons
- Monsoon impact
- Marketing campaigns
- Sale events

**Output**:
- Daily demand forecast (30/60/90 days)
- Lower bound (confidence interval)
- Upper bound (confidence interval)
- Recommended reorder quantity
- Predicted stockout date

**Festival Multipliers**:
- Diwali: 2.5x (Fashion), 3.0x (Electronics)
- Raksha Bandhan: 2.0x (Gifts)
- Valentine's Day: 1.8x (Gifts, Fashion)
- Wedding Season (Oct-Feb): 1.5x (Fashion, Jewelry)

**Model Performance**:
- MAPE (Mean Absolute Percentage Error): <20%
- RMSE: Tracked and monitored
- Updated: Weekly

---

#### Pin Code Risk Scoring
**Input Features**:
- Historical RTO rate (last 90 days)
- Total orders delivered
- COD payment percentage
- Average order value
- Tier classification (1/2/3)
- Courier performance in area
- Delivery success rate
- Monsoon impact (seasonal)

**Output**:
- Risk Score: 0-100
- Risk Level: Low (0-39), Medium (40-69), High (70-100)
- Recommended Actions

**Scoring Logic**:
```
Base Score = Historical RTO Rate × 2
Adjustments:
  + COD percentage × 0.5
  + Tier (Tier 3 adds +10, Tier 2 adds +5)
  - Delivery success rate × 0.3

Final Score = Min(100, Max(0, Adjusted Score))
```

---

### 3. GST Calculations

#### Tax Rates
```
IGST (Inter-state): 18% (standard)
CGST + SGST (Intra-state): 9% + 9% = 18%
TCS (Tax Collected at Source): 1% (for e-commerce)
```

#### Tax Calculation Logic
```javascript
if (seller_state === buyer_state) {
  CGST = (taxable_amount × 9) / 100
  SGST = (taxable_amount × 9) / 100
  IGST = 0
} else {
  IGST = (taxable_amount × 18) / 100
  CGST = 0
  SGST = 0
}

TCS = (total_amount × 1) / 100
```

#### HSN Codes
- Automatically mapped to products
- Standard tax rates per HSN
- Bulk upload support

---

### 4. Settlement Cycles by Channel

**Shopify**: T+2 days (2 days after delivery)
**WooCommerce**: T+7 days (direct to your account)
**Amazon India**: T+7 to T+14 days
**Flipkart**: T+14 to T+21 days

**COD Remittance Tracking**:
```
Expected Remittance Date = Delivery Date + Settlement Days
Pending Amount = Total COD Orders - Remitted Amount
Delayed Remittances = Orders where Current Date > Expected Remittance Date
```

---

### 5. Performance Benchmarks

#### Industry Averages (D2C Fashion)
- Average Order Value: ₹1,500 - ₹2,500
- RTO Rate: 15-25% (COD), 5-10% (Prepaid)
- Conversion Rate: 1.5-3%
- Repeat Purchase Rate: 20-30%
- Gross Margin: 40-60%
- ROAS: 3-5x
- LTV/CAC: 3-5x

#### Tier-wise Performance
**Tier 1 Cities** (Mumbai, Delhi, Bangalore, etc.):
- RTO Rate: 8-12%
- Average Delivery: 2-3 days
- COD %: 40-50%

**Tier 2 Cities** (Pune, Jaipur, Lucknow, etc.):
- RTO Rate: 15-20%
- Average Delivery: 3-5 days
- COD %: 60-70%

**Tier 3 Cities**:
- RTO Rate: 25-35%
- Average Delivery: 5-7 days
- COD %: 75-85%

---

## Response Codes

### Success Codes
- `200 OK`: Request successful
- `201 Created`: Resource created
- `204 No Content`: Successful with no response body

### Client Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded

### Server Error Codes
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

---

## Rate Limits

**Authentication Endpoints**:
- Login: 5 requests per minute
- Register: 5 requests per minute

**API Endpoints**:
- Standard: 60 requests per minute
- Reports: 10 requests per hour
- Bulk Operations: 30 requests per minute

**Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705315200
```

---

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `limit`: Number of records (default: 50, max: 1000)
- `offset`: Skip N records (default: 0)

**Example**:
```
GET /analytics/daily-metrics?limit=100&offset=200
```

**Response Headers**:
```
X-Total-Count: 543
X-Page-Limit: 100
X-Page-Offset: 200
```

---

## Error Response Format

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

---

## Date & Time Formats

**Dates**: ISO 8601 format (`YYYY-MM-DD`)
```
2024-01-15
```

**Timestamps**: ISO 8601 with timezone (`YYYY-MM-DDTHH:MM:SSZ`)
```
2024-01-15T10:30:00Z
```

**Timezone**: All timestamps in UTC, convert to IST on frontend
```javascript
// Convert UTC to IST (UTC+5:30)
const istTime = new Date(utcTimestamp).toLocaleString('en-IN', {
  timeZone: 'Asia/Kolkata'
});
```

---

## Best Practices for Frontend

### 1. Data Caching
- Cache dashboard data for 5 minutes
- Cache reports for 1 hour
- Invalidate on user actions

### 2. Real-time Updates
- Poll analytics every 5 minutes
- Poll stock alerts every 10 minutes
- Use webhooks for instant order updates

### 3. Performance
- Lazy load tables with pagination
- Infinite scroll for long lists
- Debounce search inputs (300ms)

### 4. Error Handling
```javascript
try {
  const response = await api.get('/analytics/dashboard');
  // Handle success
} catch (error) {
  if (error.response?.status === 401) {
    // Redirect to login
  } else if (error.response?.status === 429) {
    // Show rate limit message
  } else {
    // Show generic error
  }
}
```

### 5. Date Range Handling
```javascript
// Default to last 30 days if not specified
const defaultStartDate = new Date();
defaultStartDate.setDate(defaultStartDate.getDate() - 30);

const params = {
  start_date: startDate || defaultStartDate.toISOString().split('T')[0],
  end_date: endDate || new Date().toISOString().split('T')[0]
};
```

---

## Testing the API

### Using cURL
```bash
# Login
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Get Dashboard (with token)
curl -X GET "https://api.yourdomain.com/api/v1/analytics/dashboard?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using Postman
1. Import the API collection
2. Set environment variables:
   - `base_url`: `https://api.yourdomain.com`
   - `access_token`: Your JWT token
3. Use `{{base_url}}` and `{{access_token}}` in requests

---

## Support & Documentation

**API Documentation**: `/docs` (when DEBUG=True)
**Health Check**: `/health`
**API Version**: Check `X-API-Version` header in responses

**Contact**:
- Technical Support: support@yourdomain.com
- API Issues: api@yourdomain.com

---

**Last Updated**: January 2024
**API Version**: v1.0.0
