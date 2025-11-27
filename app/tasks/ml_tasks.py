"""
ML tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import datetime, timedelta


@celery_app.task(name="app.tasks.ml_tasks.train_rto_prediction_model")
def train_rto_prediction_model(tenant_id: int):
    """
    Train RTO prediction model

    Runs weekly on Sunday at 2 AM.
    """
    from app.db.session import get_sync_db
    from app.services.ml.rto_prediction import RTOPredictionService

    db = next(get_sync_db())

    try:
        service = RTOPredictionService(db, tenant_id)
        result = service.train_model()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "accuracy": result.get("accuracy", 0),
            "model_version": result.get("model_version"),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.ml_tasks.train_demand_forecast_model")
def train_demand_forecast_model(tenant_id: int):
    """
    Train demand forecasting model

    Runs weekly on Sunday at 2 AM.
    """
    from app.db.session import get_sync_db
    from app.services.ml.demand_forecast import DemandForecastService

    db = next(get_sync_db())

    try:
        service = DemandForecastService(db, tenant_id)
        result = service.train_model()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "mape": result.get("mape", 0),
            "model_version": result.get("model_version"),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.ml_tasks.train_pincode_risk_model")
def train_pincode_risk_model(tenant_id: int):
    """
    Train pin code risk scoring model

    Runs weekly on Sunday at 2 AM.
    """
    from app.db.session import get_sync_db
    from app.services.ml.pincode_risk import PinCodeRiskService

    db = next(get_sync_db())

    try:
        service = PinCodeRiskService(db, tenant_id)
        result = service.train_model()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "accuracy": result.get("accuracy", 0),
            "pincodes_analyzed": result.get("pincodes_count", 0),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
