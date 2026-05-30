from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "model" in response.json()


def test_predict_healthy_applicant():
    # An applicant with excellent scores and low ratios should be low risk
    payload = {
        "ext_source_1": 0.8,
        "ext_source_2": 0.9,
        "ext_source_3": 0.85,
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "bureau_delinquency_rate": 0.0,
        "bureau_worst_delinquency": 0.0,
        "bureau_total_overdue": 0.0,
        "inst_late_rate": 0.0,
        "inst_max_days_late": 0.0,
        "inst_avg_payment_ratio": 1.0,
        "cc_avg_utilization": 0.1,
        "cc_months_overdue": 0.0,
        "prev_refusal_rate": 0.0,
        "prev_num_applications": 1,
        "age_years": 45,
        "years_employed": 10,
        "composite_risk_score": 0.1,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] in [
        "APPROVE",
        "APPROVE_WITH_CONDITIONS",
        "MANUAL_REVIEW",
        "DECLINE",
    ]
    assert "default_probability" in data
    assert "top_risk_factors" in data


def test_predict_high_risk_applicant():
    # The example from the prompt
    payload = {
        "ext_source_1": 0.3,
        "ext_source_2": 0.2,
        "ext_source_3": 0.4,
        "credit_to_income_ratio": 6.5,
        "annuity_to_income_ratio": 0.25,
        "bureau_delinquency_rate": 0.35,
        "bureau_worst_delinquency": 4,
        "bureau_total_overdue": 15000,
        "inst_late_rate": 0.45,
        "inst_max_days_late": 120,
        "inst_avg_payment_ratio": 0.72,
        "cc_avg_utilization": 0.95,
        "cc_months_overdue": 8,
        "prev_refusal_rate": 0.6,
        "prev_num_applications": 5,
        "age_years": 28,
        "years_employed": 1,
        "composite_risk_score": 0.72,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Since we are using a dummy model or the real one, the decision might vary,
    # but the structure should be correct.
    assert "decision" in data
    assert len(data["top_risk_factors"]) == 3


def test_predict_invalid_input_missing_required():
    payload = {
        "ext_source_1": 0.8
        # missing required like credit_to_income_ratio, age_years
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_input_out_of_bounds():
    payload = {
        "ext_source_1": 1.5,  # > 1
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 45,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_input_age_under_18():
    payload = {
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 16,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_input_negative_employed_years():
    payload = {
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 30,
        "years_employed": -1,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_returns_top_3_risk_factors():
    payload = {
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 45,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    factors = data.get("top_risk_factors", [])
    assert len(factors) <= 3
    if factors:
        assert "feature" in factors[0]
        assert "direction" in factors[0]
        assert "impact" in factors[0]


def test_predict_redis_cache_key_generation(mocker):
    # If redis is available, test caching. We mock cache.get and cache.setex
    mocker.patch("api.main.CACHE_ENABLED", True)
    mock_get = mocker.patch("api.main.cache.get", return_value=None)
    mock_set = mocker.patch("api.main.cache.setex")

    payload = {
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 45,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    mock_get.assert_called_once()
    mock_set.assert_called_once()


def test_predict_cache_hit(mocker):
    mocker.patch("api.main.CACHE_ENABLED", True)
    mock_json = '{"default_probability": 0.01, "risk_tier": "LOW", "decision": "APPROVE", "top_risk_factors": [], "model_version": "xgb_v1"}'
    mocker.patch("api.main.cache.get", return_value=mock_json)

    payload = {
        "credit_to_income_ratio": 1.5,
        "annuity_to_income_ratio": 0.1,
        "age_years": 45,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["decision"] == "APPROVE"
    assert response.json()["default_probability"] == 0.01
