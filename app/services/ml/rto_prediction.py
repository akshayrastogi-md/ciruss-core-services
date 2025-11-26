"""
RTO Prediction ML Service
"""
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import boto3
from io import BytesIO

from app.models.order import Order, OrderStatus
from app.models.ml_model import MLModel
from app.core.config import settings


class RTOPredictionService:
    """RTO Prediction ML Service"""

    def __init__(self):
        self.model = None
        self.feature_columns = [
            "order_value",
            "payment_method_cod",
            "customer_type_new",
            "day_of_week",
            "pincode_historical_rto_rate",
            "category_electronics",
            "category_fashion",
            "category_food",
            "category_beauty",
        ]

    async def train_model(self, db: AsyncSession) -> MLModel:
        """
        Train RTO prediction model
        """
        # Get training data (last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        result = await db.execute(
            select(Order).where(
                and_(
                    Order.order_date >= six_months_ago,
                    Order.status.in_([
                        OrderStatus.DELIVERED,
                        OrderStatus.RTO_DELIVERED,
                    ]),
                )
            ).limit(100000)
        )
        orders = result.scalars().all()

        if len(orders) < settings.RTO_MODEL_MIN_SAMPLES:
            raise ValueError(f"Insufficient training samples. Need at least {settings.RTO_MODEL_MIN_SAMPLES}")

        # Prepare training data
        df = await self._prepare_training_data(orders, db)

        # Split data
        X = df[self.feature_columns]
        y = df["is_rto"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric="logloss",
        )

        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc_roc = roc_auc_score(y_test, y_pred_proba)

        # Save model to S3
        model_path = await self._save_model_to_s3(model)

        # Get feature importance
        feature_importance = dict(zip(self.feature_columns, model.feature_importances_.tolist()))

        # Create ML model record
        ml_model = MLModel(
            model_name="rto_prediction",
            version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            model_type="xgboost",
            trained_at=datetime.utcnow(),
            training_samples=len(orders),
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            auc_roc=float(auc_roc),
            features=self.feature_columns,
            feature_importance=feature_importance,
            model_path=model_path,
            is_active=True,
            is_deployed=False,
        )

        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        self.model = model
        return ml_model

    async def predict(self, order_data: Dict) -> Dict:
        """
        Predict RTO probability for an order
        """
        if self.model is None:
            await self.load_latest_model()

        # Prepare features
        features = self._prepare_features(order_data)

        # Make prediction
        probability = self.model.predict_proba([features])[0][1]
        risk_score = int(probability * 100)

        # Determine risk level
        if risk_score >= 70:
            risk_level = "High"
        elif risk_score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "rto_probability": float(probability),
            "risk_score": risk_score,
            "risk_level": risk_level,
        }

    async def load_latest_model(self):
        """
        Load the latest trained model from S3
        """
        # TODO: Implement loading from S3
        pass

    async def _prepare_training_data(self, orders, db: AsyncSession) -> pd.DataFrame:
        """
        Prepare training data from orders
        """
        data = []

        for order in orders:
            data.append({
                "order_value": float(order.total_amount),
                "payment_method_cod": 1 if order.payment_method.value == "cod" else 0,
                "customer_type_new": 1 if order.customer_type == "new" else 0,
                "day_of_week": order.order_date.weekday(),
                "pincode_historical_rto_rate": 0.15,  # TODO: Calculate from pincode metrics
                "category_electronics": 0,  # TODO: Get from order items
                "category_fashion": 0,
                "category_food": 0,
                "category_beauty": 0,
                "is_rto": 1 if order.status == OrderStatus.RTO_DELIVERED else 0,
            })

        return pd.DataFrame(data)

    def _prepare_features(self, order_data: Dict) -> list:
        """
        Prepare features for prediction
        """
        features = [
            order_data.get("total_amount", 0),
            1 if order_data.get("payment_method") == "cod" else 0,
            1 if order_data.get("customer_type") == "new" else 0,
            order_data.get("day_of_week", 0),
            order_data.get("pincode_historical_rto_rate", 0.15),
            1 if order_data.get("category") == "electronics" else 0,
            1 if order_data.get("category") == "fashion" else 0,
            1 if order_data.get("category") == "food" else 0,
            1 if order_data.get("category") == "beauty" else 0,
        ]
        return features

    async def _save_model_to_s3(self, model) -> str:
        """
        Save model to S3 and return path
        """
        # Serialize model
        model_bytes = BytesIO()
        pickle.dump(model, model_bytes)
        model_bytes.seek(0)

        # Upload to S3
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"ml_models/rto_prediction_{timestamp}.pkl"

        s3_client.upload_fileobj(
            model_bytes,
            settings.AWS_S3_BUCKET,
            key,
        )

        return f"s3://{settings.AWS_S3_BUCKET}/{key}"
