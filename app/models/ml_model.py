"""
ML model tracking models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, JSON, Text, Index
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel, BaseModel


class MLModel(BaseModel):
    """ML model tracking"""

    __tablename__ = "ml_models"

    # Model Info
    model_name = Column(String(100), nullable=False)  # rto_prediction, demand_forecast, pincode_risk
    version = Column(String(50), nullable=False)
    model_type = Column(String(50), nullable=False)  # xgboost, prophet, random_forest

    # Training
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_samples = Column(Integer, nullable=False)
    training_duration_seconds = Column(Integer, nullable=True)

    # Performance Metrics
    accuracy = Column(DECIMAL(5, 4), nullable=True)
    precision = Column(DECIMAL(5, 4), nullable=True)
    recall = Column(DECIMAL(5, 4), nullable=True)
    f1_score = Column(DECIMAL(5, 4), nullable=True)
    auc_roc = Column(DECIMAL(5, 4), nullable=True)
    mape = Column(DECIMAL(10, 4), nullable=True)  # Mean Absolute Percentage Error
    rmse = Column(DECIMAL(10, 4), nullable=True)  # Root Mean Square Error

    # Features
    features = Column(JSON, default=[])  # List of feature names
    feature_importance = Column(JSON, default={})  # {feature: importance}

    # Storage
    model_path = Column(String(1000), nullable=False)  # S3 path
    model_size_mb = Column(DECIMAL(10, 2), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_deployed = Column(Boolean, default=False)

    # Metadata
    hyperparameters = Column(JSON, default={})
    training_config = Column(JSON, default={})
    notes = Column(Text, nullable=True)


class MLPrediction(TenantBaseModel):
    """ML prediction tracking"""

    __tablename__ = "ml_predictions"
    __table_args__ = (
        Index("idx_prediction_tenant_type", "tenant_id", "prediction_type"),
    )

    # Model Info
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=True)
    prediction_type = Column(String(50), nullable=False)  # rto, demand, risk_score

    # Entity
    entity_type = Column(String(50), nullable=False)  # order, product, pincode
    entity_id = Column(Integer, nullable=False)

    # Prediction
    prediction_value = Column(DECIMAL(10, 4), nullable=False)
    confidence_score = Column(DECIMAL(5, 4), nullable=True)

    # Features Used
    features = Column(JSON, default={})

    # Actual Outcome (for feedback loop)
    actual_value = Column(DECIMAL(10, 4), nullable=True)
    outcome_recorded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    model = relationship("MLModel", foreign_keys=[model_id])
