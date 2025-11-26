"""
Demand Forecasting ML Service using Prophet
"""
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import boto3
from io import BytesIO

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.ml_model import MLModel
from app.core.config import settings


class DemandForecastService:
    """Demand Forecasting ML Service using Facebook Prophet"""

    # Indian festivals database
    INDIAN_FESTIVALS = {
        2024: [
            {'date': '2024-01-26', 'name': 'Republic Day', 'multiplier': 1.3},
            {'date': '2024-03-08', 'name': 'Holi', 'multiplier': 1.8},
            {'date': '2024-03-25', 'name': 'Ugadi', 'multiplier': 1.4},
            {'date': '2024-04-11', 'name': 'Eid', 'multiplier': 1.6},
            {'date': '2024-08-15', 'name': 'Independence Day', 'multiplier': 1.3},
            {'date': '2024-08-26', 'name': 'Raksha Bandhan', 'multiplier': 1.7},
            {'date': '2024-09-16', 'name': 'Ganesh Chaturthi', 'multiplier': 1.5},
            {'date': '2024-10-12', 'name': 'Dussehra', 'multiplier': 1.6},
            {'date': '2024-11-01', 'name': 'Diwali', 'multiplier': 2.5},
            {'date': '2024-12-25', 'name': 'Christmas', 'multiplier': 1.5},
        ],
        2025: [
            {'date': '2025-01-26', 'name': 'Republic Day', 'multiplier': 1.3},
            {'date': '2025-02-14', 'name': 'Valentine\'s Day', 'multiplier': 1.4},
            {'date': '2025-03-14', 'name': 'Holi', 'multiplier': 1.8},
            {'date': '2025-03-30', 'name': 'Eid', 'multiplier': 1.6},
            {'date': '2025-04-14', 'name': 'Ugadi', 'multiplier': 1.4},
            {'date': '2025-08-09', 'name': 'Raksha Bandhan', 'multiplier': 1.7},
            {'date': '2025-08-15', 'name': 'Independence Day', 'multiplier': 1.3},
            {'date': '2025-08-27', 'name': 'Ganesh Chaturthi', 'multiplier': 1.5},
            {'date': '2025-09-30', 'name': 'Dussehra', 'multiplier': 1.6},
            {'date': '2025-10-20', 'name': 'Diwali', 'multiplier': 2.5},
            {'date': '2025-12-25', 'name': 'Christmas', 'multiplier': 1.5},
        ],
    }

    # Wedding seasons
    WEDDING_MONTHS = [10, 11, 12, 1, 2, 4, 5, 6]  # Oct-Feb, Apr-Jun

    # Monsoon months
    MONSOON_MONTHS = [6, 7, 8, 9]  # Jun-Sep

    def __init__(self):
        self.model = None
        self.product_models = {}

    async def train_model(
        self,
        db: AsyncSession,
        tenant_id: int,
        product_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> MLModel:
        """
        Train demand forecasting model
        """
        # Get training data (6-24 months of order history)
        min_history_days = settings.DEMAND_FORECAST_MIN_HISTORY_DAYS
        start_date = datetime.utcnow() - timedelta(days=min_history_days * 2)

        # Build query
        query = (
            select(
                func.date(Order.order_date).label('date'),
                func.sum(OrderItem.quantity).label('quantity'),
            )
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.order_date >= start_date,
                )
            )
            .group_by(func.date(Order.order_date))
        )

        # Filter by product or category
        if product_id:
            query = query.where(OrderItem.product_id == product_id)
        elif category:
            query = query.join(Product, OrderItem.product_id == Product.id)
            query = query.where(Product.category == category)

        result = await db.execute(query)
        data = result.all()

        if len(data) < 30:  # Need at least 30 days of data
            raise ValueError(f"Insufficient data. Need at least 30 days of sales history")

        # Prepare training data
        df = pd.DataFrame(data, columns=['date', 'quantity'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.rename(columns={'date': 'ds', 'quantity': 'y'})

        # Add regressors
        df = self._add_regressors(df)

        # Initialize Prophet model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative',
        )

        # Add custom seasonalities
        model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

        # Add regressors
        model.add_regressor('is_festival')
        model.add_regressor('festival_impact')
        model.add_regressor('is_wedding_season')
        model.add_regressor('is_monsoon')

        # Fit model
        model.fit(df)

        # Make predictions on historical data for validation
        forecast = model.predict(df)

        # Calculate metrics
        y_true = df['y'].values
        y_pred = forecast['yhat'].values
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))

        # Save model to S3
        model_path = await self._save_model_to_s3(model, tenant_id, product_id, category)

        # Create ML model record
        model_name = "demand_forecast"
        if product_id:
            model_name += f"_product_{product_id}"
        elif category:
            model_name += f"_category_{category}"

        ml_model = MLModel(
            model_name=model_name,
            version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            model_type="prophet",
            trained_at=datetime.utcnow(),
            training_samples=len(data),
            mape=float(mape),
            rmse=float(rmse),
            features=['is_festival', 'festival_impact', 'is_wedding_season', 'is_monsoon'],
            model_path=model_path,
            is_active=True,
            is_deployed=True,
        )

        db.add(ml_model)
        await db.commit()
        await db.refresh(ml_model)

        self.model = model
        return ml_model

    async def forecast_demand(
        self,
        db: AsyncSession,
        tenant_id: int,
        days: int = 30,
        product_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Dict:
        """
        Forecast demand for next N days
        """
        if self.model is None:
            # Load latest model
            await self._load_latest_model(db, tenant_id, product_id, category)

        # Create future dataframe
        future = self.model.make_future_dataframe(periods=days)
        future = self._add_regressors(future)

        # Make predictions
        forecast = self.model.predict(future)

        # Get only future predictions
        forecast_future = forecast.tail(days)

        # Prepare response
        predictions = []
        for idx, row in forecast_future.iterrows():
            predictions.append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'predicted_demand': max(0, int(row['yhat'])),
                'lower_bound': max(0, int(row['yhat_lower'])),
                'upper_bound': max(0, int(row['yhat_upper'])),
                'confidence': self._calculate_confidence(row),
            })

        # Calculate stockout predictions
        stockout_alerts = await self._predict_stockouts(
            db, tenant_id, predictions, product_id, category
        )

        return {
            'forecast_period_days': days,
            'predictions': predictions,
            'total_forecasted_demand': sum(p['predicted_demand'] for p in predictions),
            'stockout_alerts': stockout_alerts,
            'model_metrics': {
                'mape': getattr(self.model, 'mape', None),
                'rmse': getattr(self.model, 'rmse', None),
            },
        }

    def _add_regressors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add custom regressors to dataframe"""
        df = df.copy()

        # Festival regressor
        df['is_festival'] = 0
        df['festival_impact'] = 0

        for year, festivals in self.INDIAN_FESTIVALS.items():
            for festival in festivals:
                festival_date = pd.to_datetime(festival['date'])
                # Mark 3 days before to 3 days after festival
                mask = (df['ds'] >= festival_date - timedelta(days=3)) & \
                       (df['ds'] <= festival_date + timedelta(days=3))
                df.loc[mask, 'is_festival'] = 1
                df.loc[mask, 'festival_impact'] = festival['multiplier'] - 1

        # Wedding season regressor
        df['is_wedding_season'] = df['ds'].dt.month.isin(self.WEDDING_MONTHS).astype(int)

        # Monsoon regressor
        df['is_monsoon'] = df['ds'].dt.month.isin(self.MONSOON_MONTHS).astype(int)

        return df

    def _calculate_confidence(self, row: pd.Series) -> float:
        """Calculate confidence score for prediction"""
        # Confidence based on prediction interval width
        interval_width = row['yhat_upper'] - row['yhat_lower']
        predicted = row['yhat']

        if predicted <= 0:
            return 0.5

        relative_width = interval_width / predicted

        # Lower relative width = higher confidence
        if relative_width < 0.2:
            confidence = 0.95
        elif relative_width < 0.4:
            confidence = 0.85
        elif relative_width < 0.6:
            confidence = 0.75
        else:
            confidence = 0.65

        return confidence

    async def _predict_stockouts(
        self,
        db: AsyncSession,
        tenant_id: int,
        predictions: List[Dict],
        product_id: Optional[int],
        category: Optional[str],
    ) -> List[Dict]:
        """Predict stockout dates based on current inventory and forecast"""
        alerts = []

        # Get current stock
        if product_id:
            result = await db.execute(
                select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_id == tenant_id,
                    )
                )
            )
            product = result.scalar_one_or_none()
            if product:
                current_stock = product.total_stock
                cumulative_demand = 0

                for pred in predictions:
                    cumulative_demand += pred['predicted_demand']
                    if cumulative_demand >= current_stock:
                        days_until_stockout = predictions.index(pred) + 1

                        alerts.append({
                            'product_id': product_id,
                            'product_name': product.name,
                            'current_stock': current_stock,
                            'predicted_stockout_date': pred['date'],
                            'days_until_stockout': days_until_stockout,
                            'severity': 'critical' if days_until_stockout < 7 else 'high' if days_until_stockout < 14 else 'medium',
                            'recommended_reorder_quantity': int(cumulative_demand * 1.2),  # 20% buffer
                        })
                        break

        return alerts

    async def _load_latest_model(
        self,
        db: AsyncSession,
        tenant_id: int,
        product_id: Optional[int],
        category: Optional[str],
    ):
        """Load the latest trained model from database"""
        model_name = "demand_forecast"
        if product_id:
            model_name += f"_product_{product_id}"
        elif category:
            model_name += f"_category_{category}"

        result = await db.execute(
            select(MLModel)
            .where(
                and_(
                    MLModel.model_name == model_name,
                    MLModel.is_deployed == True,
                )
            )
            .order_by(MLModel.trained_at.desc())
            .limit(1)
        )
        ml_model = result.scalar_one_or_none()

        if ml_model:
            # Load from S3
            self.model = await self._load_model_from_s3(ml_model.model_path)
        else:
            raise ValueError(f"No trained model found for {model_name}")

    async def _save_model_to_s3(
        self,
        model,
        tenant_id: int,
        product_id: Optional[int],
        category: Optional[str],
    ) -> str:
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
        identifier = f"product_{product_id}" if product_id else f"category_{category}" if category else "overall"
        key = f"ml_models/demand_forecast_tenant_{tenant_id}_{identifier}_{timestamp}.pkl"

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

        # Parse S3 path
        bucket = s3_path.split('/')[2]
        key = '/'.join(s3_path.split('/')[3:])

        model_bytes = BytesIO()
        s3_client.download_fileobj(bucket, key, model_bytes)
        model_bytes.seek(0)

        return pickle.load(model_bytes)
