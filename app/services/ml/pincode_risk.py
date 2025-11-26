"""
Pin Code Risk Scoring ML Service
"""
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import boto3
from io import BytesIO

from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.analytics import PinCodeMetrics
from app.models.ml_model import MLModel
from app.core.config import settings


class PinCodeRiskService:
    """Pin Code Risk Scoring ML Service"""

    def __init__(self):
        self.model = None
        self.feature_columns = [
            'historical_rto_rate',
            'total_orders',
            'cod_percentage',
            'avg_order_value',
            'tier_1',
            'tier_2',
            'tier_3',
            'delivery_success_rate',
        ]

    async def train_model(self, db: AsyncSession, tenant_id: int) -> MLModel:
        """
        Train pin code risk scoring model
        """
        # Get pin code metrics
        result = await db.execute(
            select(PinCodeMetrics).where(
                and_(
                    PinCodeMetrics.tenant_id == tenant_id,
                    PinCodeMetrics.total_orders >= 20,  # Minimum orders for training
                )
            )
        )
        pincodes = result.scalars().all()

        if len(pincodes) < 50:
            raise ValueError(f"Insufficient pin codes. Need at least 50 pin codes with 20+ orders")

        # Prepare training data
        df = await self._prepare_training_data(pincodes)

        # Split data
        X = df[self.feature_columns]
        y = df['is_high_risk']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
        )

        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # Save model to S3
        model_path = await self._save_model_to_s3(model, tenant_id)

        # Get feature importance
        feature_importance = dict(zip(self.feature_columns, model.feature_importances_.tolist()))

        # Create ML model record
        ml_model = MLModel(
            model_name="pincode_risk_scoring",
            version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            model_type="random_forest",
            trained_at=datetime.utcnow(),
            training_samples=len(pincodes),
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            features=self.feature_columns,
            feature_importance=feature_importance,
            model_path=model_path,
            is_active=True,
            is_deployed=True,
        )

        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        self.model = model
        return ml_model

    async def calculate_risk_score(
        self,
        db: AsyncSession,
        tenant_id: int,
        pincode: str,
    ) -> Dict:
        """
        Calculate risk score for a pin code
        """
        # Get pin code metrics
        result = await db.execute(
            select(PinCodeMetrics).where(
                and_(
                    PinCodeMetrics.tenant_id == tenant_id,
                    PinCodeMetrics.pincode == pincode,
                )
            )
        )
        pincode_metrics = result.scalar_one_or_none()

        if not pincode_metrics:
            # New pin code - calculate from scratch
            pincode_metrics = await self._calculate_pincode_metrics(db, tenant_id, pincode)

        # Calculate risk score
        if pincode_metrics.total_orders < 10:
            # Insufficient data - use default risk score
            risk_score = 50
            risk_level = "Medium"
            confidence = 0.5
        else:
            # Load model and predict
            if self.model is None:
                await self._load_latest_model(db, tenant_id)

            features = self._prepare_features(pincode_metrics)
            risk_probability = self.model.predict_proba([features])[0][1]
            risk_score = int(risk_probability * 100)
            confidence = max(self.model.predict_proba([features])[0])

            # Determine risk level
            if risk_score >= 70:
                risk_level = "High"
            elif risk_score >= 40:
                risk_level = "Medium"
            else:
                risk_level = "Low"

        # Update pin code metrics
        pincode_metrics.risk_score = risk_score
        pincode_metrics.risk_level = risk_level
        await db.commit()

        return {
            'pincode': pincode,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'confidence': float(confidence),
            'metrics': {
                'total_orders': pincode_metrics.total_orders,
                'rto_rate': float(pincode_metrics.rto_rate),
                'cod_percentage': float(pincode_metrics.cod_orders / pincode_metrics.total_orders * 100) if pincode_metrics.total_orders > 0 else 0,
                'avg_order_value': float(pincode_metrics.avg_order_value),
                'tier': pincode_metrics.tier,
            },
            'recommendations': self._get_recommendations(risk_score, risk_level, pincode_metrics),
        }

    async def _calculate_pincode_metrics(
        self,
        db: AsyncSession,
        tenant_id: int,
        pincode: str,
    ) -> PinCodeMetrics:
        """Calculate metrics for a pin code"""
        # Get orders for this pin code
        result = await db.execute(
            select(Order).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.shipping_pincode == pincode,
                )
            )
        )
        orders = result.scalars().all()

        if not orders:
            # Create default metrics
            metrics = PinCodeMetrics(
                tenant_id=tenant_id,
                pincode=pincode,
                tier="3",  # Default to tier 3
                total_orders=0,
                total_revenue=0,
                avg_order_value=0,
                delivered_orders=0,
                rto_orders=0,
                rto_rate=0,
                avg_delivery_days=0,
                cod_orders=0,
                cod_rto_rate=0,
            )
            db.add(metrics)
            await db.commit()
            return metrics

        # Calculate metrics
        total_orders = len(orders)
        delivered_orders = sum(1 for o in orders if o.status == OrderStatus.DELIVERED)
        rto_orders = sum(1 for o in orders if o.status == OrderStatus.RTO_DELIVERED)
        cod_orders = sum(1 for o in orders if o.payment_method == PaymentMethod.COD)
        total_revenue = sum(float(o.total_amount) for o in orders)

        metrics = PinCodeMetrics(
            tenant_id=tenant_id,
            pincode=pincode,
            city=orders[0].shipping_city if orders else None,
            state=orders[0].shipping_state if orders else None,
            tier=self._determine_tier(pincode, orders[0].shipping_city if orders else None),
            total_orders=total_orders,
            total_revenue=total_revenue,
            avg_order_value=total_revenue / total_orders if total_orders > 0 else 0,
            delivered_orders=delivered_orders,
            rto_orders=rto_orders,
            rto_rate=(rto_orders / total_orders * 100) if total_orders > 0 else 0,
            avg_delivery_days=5,  # TODO: Calculate from shipment data
            cod_orders=cod_orders,
            cod_rto_rate=(sum(1 for o in orders if o.payment_method == PaymentMethod.COD and o.status == OrderStatus.RTO_DELIVERED) / cod_orders * 100) if cod_orders > 0 else 0,
            last_order_date=max(o.order_date.date() for o in orders) if orders else None,
        )

        db.add(metrics)
        await db.commit()
        await db.refresh(metrics)

        return metrics

    def _determine_tier(self, pincode: str, city: Optional[str]) -> str:
        """Determine tier based on pincode and city"""
        # Tier 1 cities
        tier_1_cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Ahmedabad', 'Chennai', 'Kolkata', 'Pune', 'Surat']

        # Tier 2 cities
        tier_2_cities = ['Jaipur', 'Lucknow', 'Kanpur', 'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri-Chinchwad', 'Patna']

        if city:
            if any(t1 in city for t1 in tier_1_cities):
                return "1"
            elif any(t2 in city for t2 in tier_2_cities):
                return "2"

        return "3"

    async def _prepare_training_data(self, pincodes: list) -> pd.DataFrame:
        """Prepare training data from pin code metrics"""
        data = []

        for pc in pincodes:
            data.append({
                'historical_rto_rate': float(pc.rto_rate),
                'total_orders': pc.total_orders,
                'cod_percentage': (pc.cod_orders / pc.total_orders * 100) if pc.total_orders > 0 else 0,
                'avg_order_value': float(pc.avg_order_value),
                'tier_1': 1 if pc.tier == "1" else 0,
                'tier_2': 1 if pc.tier == "2" else 0,
                'tier_3': 1 if pc.tier == "3" else 0,
                'delivery_success_rate': (pc.delivered_orders / pc.total_orders * 100) if pc.total_orders > 0 else 0,
                'is_high_risk': 1 if pc.rto_rate >= 15 else 0,  # 15% RTO rate threshold
            })

        return pd.DataFrame(data)

    def _prepare_features(self, pincode_metrics: PinCodeMetrics) -> list:
        """Prepare features for prediction"""
        features = [
            float(pincode_metrics.rto_rate),
            pincode_metrics.total_orders,
            (pincode_metrics.cod_orders / pincode_metrics.total_orders * 100) if pincode_metrics.total_orders > 0 else 0,
            float(pincode_metrics.avg_order_value),
            1 if pincode_metrics.tier == "1" else 0,
            1 if pincode_metrics.tier == "2" else 0,
            1 if pincode_metrics.tier == "3" else 0,
            (pincode_metrics.delivered_orders / pincode_metrics.total_orders * 100) if pincode_metrics.total_orders > 0 else 0,
        ]
        return features

    def _get_recommendations(
        self,
        risk_score: int,
        risk_level: str,
        metrics: PinCodeMetrics,
    ) -> List[str]:
        """Get recommendations based on risk score"""
        recommendations = []

        if risk_level == "High":
            recommendations.append("Consider rejecting COD orders for this pin code")
            recommendations.append("Require prepaid payment for orders above ₹1000")
            recommendations.append("Implement additional verification for new customers")
        elif risk_level == "Medium":
            recommendations.append("Review COD orders manually before shipment")
            recommendations.append("Consider offering prepaid discounts")
            recommendations.append("Monitor RTO trends closely")
        else:
            recommendations.append("Pin code is safe for COD orders")
            recommendations.append("Consider offering COD on all order values")

        if metrics.cod_rto_rate > 20:
            recommendations.append(f"COD RTO rate is high ({metrics.cod_rto_rate:.1f}%) - review courier partner")

        return recommendations

    async def _load_latest_model(self, db: AsyncSession, tenant_id: int):
        """Load the latest trained model from database"""
        result = await db.execute(
            select(MLModel)
            .where(
                and_(
                    MLModel.model_name == "pincode_risk_scoring",
                    MLModel.is_deployed == True,
                )
            )
            .order_by(MLModel.trained_at.desc())
            .limit(1)
        )
        ml_model = result.scalar_one_or_none()

        if ml_model:
            self.model = await self._load_model_from_s3(ml_model.model_path)
        else:
            raise ValueError("No trained model found for pincode_risk_scoring")

    async def _save_model_to_s3(self, model, tenant_id: int) -> str:
        """Save model to S3 and return path"""
        model_bytes = BytesIO()
        pickle.dump(model, model_bytes)
        model_bytes.seek(0)

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"ml_models/pincode_risk_tenant_{tenant_id}_{timestamp}.pkl"

        s3_client.upload_fileobj(
            model_bytes,
            settings.AWS_S3_BUCKET,
            key,
        )

        return f"s3://{settings.AWS_S3_BUCKET}/{key}"

    async def _load_model_from_s3(self, s3_path: str):
        """Load model from S3"""
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        bucket = s3_path.split('/')[2]
        key = '/'.join(s3_path.split('/')[3:])

        model_bytes = BytesIO()
        s3_client.download_fileobj(bucket, key, model_bytes)
        model_bytes.seek(0)

        return pickle.load(model_bytes)
