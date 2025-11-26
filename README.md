# D2C Analytics Platform - Backend Service

A production-ready backend service for Indian D2C e-commerce brands with multi-channel integration, COD/RTO analytics with ML, GST compliance, and AI-powered demand forecasting.

## 🚀 Features

### Core Features
- **Multi-Channel Integration**: Shopify, WooCommerce, Amazon India SP-API, Flipkart Seller API
- **Logistics Integration**: Shiprocket for order fulfillment, tracking, NDR management
- **Marketing Analytics**: Facebook Ads, Google Ads with ROAS calculation and attribution
- **COD/RTO Analytics**: ML-powered RTO prediction, pin code risk scoring, COD acceptance engine
- **GST Compliance**: Automatic tax calculation, GST reports, invoice generation, TCS tracking
- **AI-Powered Demand Forecasting**: Prophet-based forecasting with Indian festivals and monsoon impact
- **Inventory Management**: SKU-level profitability, stockout prediction, dead stock identification
- **Working Capital Insights**: COD remittance tracking, cash flow forecasting, payment reconciliation

### System Features
- **Authentication**: JWT-based auth with email verification and password reset
- **Multi-Tenancy**: Single database multi-tenant architecture
- **RBAC**: Role-based access control (Admin, Manager, Analyst, Finance)
- **API Key Management**: Scoped API keys with usage tracking
- **Rate Limiting**: Configurable rate limits on all endpoints
- **Background Jobs**: Celery-based task queue for sync, ML training, reports
- **Subscriptions**: Razorpay integration with usage-based billing
- **Monitoring**: Sentry error tracking with structured logging

## 🏗️ Technology Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with async SQLAlchemy
- **Cache**: Redis 7+ for sessions, caching, rate limiting
- **Task Queue**: Celery + Redis
- **ML/DS**: scikit-learn, XGBoost, Prophet, pandas, numpy
- **Cloud**: AWS S3 for file storage
- **Monitoring**: Sentry
- **Payments**: Razorpay

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- AWS Account (for S3)
- Razorpay Account

## 🔧 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd ciruss-core-services
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
# Application
SECRET_KEY=<generate-secure-key>
JWT_SECRET_KEY=<generate-secure-jwt-key>
ENCRYPTION_KEY=<generate-fernet-key>

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/d2c_analytics

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=<your-aws-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret>
AWS_S3_BUCKET=<your-bucket-name>

# Razorpay
RAZORPAY_KEY_ID=<your-razorpay-key>
RAZORPAY_KEY_SECRET=<your-razorpay-secret>

# Sentry
SENTRY_DSN=<your-sentry-dsn>
```

### 5. Generate encryption keys

```python
# For ENCRYPTION_KEY (Fernet)
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())

# For SECRET_KEY and JWT_SECRET_KEY
import secrets
print(secrets.token_urlsafe(32))
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Seed initial data

```bash
python scripts/seed_data.py
```

## 🐳 Docker Setup

### Development with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

Services:
- **API**: http://localhost:8000
- **Flower**: http://localhost:5555 (Celery monitoring)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🏃 Running Locally

### 1. Start the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Celery worker

```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

### 3. Start Celery beat (scheduler)

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

### 4. Start Flower (optional - for monitoring)

```bash
celery -A app.tasks.celery_app flower --port=5555
```

## 📚 API Documentation

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Authentication

### Register a new user

```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "company_name": "My D2C Store",
  "gstin": "22AAAAA0000A1Z5"
}
```

### Login

```bash
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "token_type": "bearer"
}
```

### Use the token

```bash
GET /api/v1/orders
Authorization: Bearer <access_token>
```

## 🗄️ Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

## 📊 Background Tasks

Scheduled tasks run automatically via Celery Beat:

- **Channel Sync**: Every 30 minutes
- **Daily Analytics**: Daily at 1 AM IST
- **ML Model Training**: Weekly on Sunday at 2 AM IST
- **Pincode Metrics Update**: Daily at 3 AM IST
- **Inventory Snapshot**: Daily at 4 AM IST
- **Stock Alerts**: Every 6 hours
- **COD Remittance Tracking**: Daily at 10 AM IST
- **Subscription Usage Check**: Every hour

## 🤖 ML Models

### RTO Prediction

```python
from app.services.ml.rto_prediction import RTOPredictionService

service = RTOPredictionService()

# Predict RTO for an order
prediction = await service.predict({
    "total_amount": 1500,
    "payment_method": "cod",
    "customer_type": "new",
    "pincode": "400001",
    "category": "electronics"
})

# Output:
{
    "rto_probability": 0.35,
    "risk_score": 35,
    "risk_level": "Low"
}
```

### Demand Forecasting

```python
from app.services.ml.demand_forecast import DemandForecastService

service = DemandForecastService()

# Get forecast for next 30 days
forecast = await service.forecast_demand(
    product_id=123,
    days=30
)
```

## 🔐 Security

### Rate Limiting

- **Login**: 5 requests/minute
- **API Endpoints**: 60 requests/minute
- **Reports**: 10 requests/hour

### Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### Password Policy

- Minimum 8 characters
- Passwords are hashed using bcrypt
- Account locked for 15 minutes after 5 failed login attempts

## 📦 Deployment

### Production Deployment (Docker)

1. **Build production image**

```bash
docker build -t d2c-analytics:latest .
```

2. **Run with environment variables**

```bash
docker run -d \
  --name d2c-api \
  -p 8000:8000 \
  --env-file .env \
  d2c-analytics:latest
```

### Environment-specific configurations

- Set `APP_ENV=production` in production
- Set `DEBUG=False` in production
- Use strong secrets and keys
- Enable HTTPS only
- Configure CORS for your frontend domain

## 📈 Monitoring

### Sentry Integration

Errors are automatically tracked in Sentry when configured.

### Logs

Structured logging with JSON output in production:

```json
{
  "timestamp": "2024-01-01T10:00:00Z",
  "level": "INFO",
  "logger": "app.api.auth",
  "message": "User logged in",
  "user_id": 123,
  "tenant_id": 456
}
```

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "app": "D2C Analytics Platform",
  "version": "1.0.0",
  "environment": "production"
}
```

## 🛠️ Development

### Code Formatting

```bash
# Format code with black
black app/

# Check code style with flake8
flake8 app/

# Type checking with mypy
mypy app/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📝 Project Structure

```
ciruss-core-services/
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/   # API endpoints
│   ├── core/                # Core configurations
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── deps.py
│   │   └── context.py
│   ├── db/                  # Database setup
│   │   ├── session.py
│   │   └── redis.py
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── channels/        # Channel integrations
│   │   ├── logistics/       # Logistics integrations
│   │   ├── marketing/       # Marketing integrations
│   │   ├── ml/              # ML services
│   │   ├── analytics/       # Analytics services
│   │   ├── gst/             # GST services
│   │   └── reports/         # Report generation
│   ├── tasks/               # Celery tasks
│   ├── middleware/          # Custom middleware
│   ├── utils/               # Utility functions
│   └── main.py              # FastAPI application
├── ml_models/               # Trained ML models
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── .env.example             # Environment variables template
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # Docker compose for development
├── Dockerfile               # Production dockerfile
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary and confidential.

## 🆘 Support

For support, email support@d2canalytics.com or open an issue in the repository.

## 🎯 Roadmap

- [ ] Implement all channel integrations
- [ ] Complete ML model implementations
- [ ] Add comprehensive test coverage
- [ ] Implement real-time websocket updates
- [ ] Add mobile app API endpoints
- [ ] Implement advanced analytics dashboards
- [ ] Add multi-language support
- [ ] Implement automated testing and CI/CD

---

**Built with ❤️ for Indian D2C Brands**
