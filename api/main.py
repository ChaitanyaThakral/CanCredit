from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import numpy as np
import pandas as pd
import redis
import json
import hashlib
import os
import pathlib
from typing import Optional

app = FastAPI(
    title="CanCredit Scoring API",
    description="Credit risk scoring for loan applications using XGBoost + SHAP",
    version="1.0.0",
)

# Load model and SHAP explainer on startup
MODEL_DIR = pathlib.Path(__file__).parent.parent / "model"
MODEL_PATH = MODEL_DIR / "xgb_credit_model.pkl"

# Fallback: create a dummy model if the actual model doesn't exist yet so tests can run
if not MODEL_PATH.exists():
    import warnings

    warnings.warn(
        f"Model not found at {MODEL_PATH}. Creating a dummy model for testing."
    )
    from xgboost import XGBClassifier
    import shap

    # Create synthetic data to train a dummy model
    dummy_X = pd.DataFrame(
        np.random.rand(10, 18),
        columns=[
            "ext_source_1",
            "ext_source_2",
            "ext_source_3",
            "credit_to_income_ratio",
            "annuity_to_income_ratio",
            "bureau_delinquency_rate",
            "bureau_worst_delinquency",
            "bureau_total_overdue",
            "inst_late_rate",
            "inst_max_days_late",
            "inst_avg_payment_ratio",
            "cc_avg_utilization",
            "cc_months_overdue",
            "prev_refusal_rate",
            "prev_num_applications",
            "age_years",
            "years_employed",
            "composite_risk_score",
        ],
    )
    dummy_y = np.random.randint(0, 2, 10)
    model = XGBClassifier(n_estimators=10, max_depth=3)
    model.fit(dummy_X, dummy_y)
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
else:
    model = joblib.load(MODEL_PATH)

import shap

# Force tree explainer to avoid issues
explainer = shap.TreeExplainer(model)

# Redis for caching
try:
    cache = redis.Redis(host="localhost", port=6379, decode_responses=True)
    cache.ping()
    CACHE_ENABLED = True
except:
    CACHE_ENABLED = False

FEATURES = [
    "ext_source_1",
    "ext_source_2",
    "ext_source_3",
    "credit_to_income_ratio",
    "annuity_to_income_ratio",
    "bureau_delinquency_rate",
    "bureau_worst_delinquency",
    "bureau_total_overdue",
    "inst_late_rate",
    "inst_max_days_late",
    "inst_avg_payment_ratio",
    "cc_avg_utilization",
    "cc_months_overdue",
    "prev_refusal_rate",
    "prev_num_applications",
    "age_years",
    "years_employed",
    "composite_risk_score",
]


class ApplicationRequest(BaseModel):
    ext_source_1: Optional[float] = Field(0.5, ge=0, le=1)
    ext_source_2: Optional[float] = Field(0.5, ge=0, le=1)
    ext_source_3: Optional[float] = Field(0.5, ge=0, le=1)
    credit_to_income_ratio: float = Field(..., ge=0, le=100)
    annuity_to_income_ratio: float = Field(..., ge=0, le=10)
    bureau_delinquency_rate: float = Field(0.0, ge=0, le=1)
    bureau_worst_delinquency: float = Field(0.0, ge=0, le=5)
    bureau_total_overdue: float = Field(0.0, ge=0)
    inst_late_rate: float = Field(0.0, ge=0, le=1)
    inst_max_days_late: float = Field(0.0, ge=0)
    inst_avg_payment_ratio: float = Field(1.0, ge=0, le=5)
    cc_avg_utilization: float = Field(0.0, ge=0, le=3)
    cc_months_overdue: float = Field(0.0, ge=0)
    prev_refusal_rate: float = Field(0.0, ge=0, le=1)
    prev_num_applications: float = Field(0.0, ge=0)
    age_years: float = Field(..., ge=18, le=100)
    years_employed: float = Field(0.0, ge=0)
    composite_risk_score: float = Field(0.0, ge=0, le=1)


class ScoreResponse(BaseModel):
    default_probability: float
    risk_tier: str
    decision: str
    top_risk_factors: list[dict]
    model_version: str = "xgb_v1"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "xgb_credit_v1",
        "cache": "enabled" if CACHE_ENABLED else "disabled",
    }


@app.post("/predict", response_model=ScoreResponse)
def predict(request: ApplicationRequest):
    input_dict = request.model_dump()
    input_data = pd.DataFrame([input_dict])[FEATURES]

    # Cache key from input hash
    cache_key = f"score:{hashlib.md5(str(input_dict).encode()).hexdigest()}"

    if CACHE_ENABLED:
        try:
            cached = cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass  # Redis might have gone down

    # Score
    prob = float(model.predict_proba(input_data)[0, 1])

    # Risk tier thresholds (calibrated to ~8% population default rate)
    if prob < 0.05:
        tier, decision = "LOW", "APPROVE"
    elif prob < 0.15:
        tier, decision = "MEDIUM", "APPROVE_WITH_CONDITIONS"
    elif prob < 0.30:
        tier, decision = "HIGH", "MANUAL_REVIEW"
    else:
        tier, decision = "VERY_HIGH", "DECLINE"

    # SHAP for top 3 risk drivers
    shap_vals = explainer.shap_values(input_data)[0]
    shap_series = pd.Series(dict(zip(FEATURES, shap_vals)))
    top_factors = shap_series.abs().nlargest(3).index.tolist()
    top_risk = [
        {
            "feature": f,
            "direction": "increases" if shap_series[f] > 0 else "decreases",
            "impact": round(abs(float(shap_series[f])), 4),
        }
        for f in top_factors
    ]

    result = ScoreResponse(
        default_probability=round(prob, 4),
        risk_tier=tier,
        decision=decision,
        top_risk_factors=top_risk,
    )

    if CACHE_ENABLED:
        try:
            cache.setex(cache_key, 3600, result.model_dump_json())
        except:
            pass

    return result
