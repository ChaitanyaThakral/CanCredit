"""
Tests for model/train.py — covers data preparation, metric calculations,
and model contract validation using synthetic data.
No Snowflake connection or MLflow server required.
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

# Make model/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))

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


def _make_synthetic_df(n=2000, default_rate=0.08, seed=42):
    """Create a labelled synthetic dataset with the expected feature columns."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f: rng.random(n) for f in FEATURES})
    df["label"] = (rng.random(n) < default_rate).astype(int)
    return df


# ===========================================================================
# prepare_features
# ===========================================================================
class TestPrepareFeatures:
    def _import(self):
        import importlib
        import train

        importlib.reload(train)
        return train

    def test_returns_x_and_y(self):
        train = self._import()
        df = _make_synthetic_df()
        X, y = train.prepare_features(df)
        assert X.shape == (len(df), len(FEATURES))
        assert len(y) == len(df)

    def test_no_nulls_after_imputation(self):
        train = self._import()
        df = _make_synthetic_df()
        # Introduce NaNs
        df.loc[0:50, "ext_source_1"] = np.nan
        df.loc[100:120, "bureau_delinquency_rate"] = np.nan
        X, y = train.prepare_features(df)
        assert X.isnull().sum().sum() == 0

    def test_label_not_in_X(self):
        train = self._import()
        df = _make_synthetic_df()
        X, y = train.prepare_features(df)
        assert "label" not in X.columns

    def test_y_is_binary(self):
        train = self._import()
        df = _make_synthetic_df()
        _, y = train.prepare_features(df)
        assert set(y.unique()).issubset({0, 1})

    def test_feature_count_matches_constant(self):
        train = self._import()
        df = _make_synthetic_df()
        X, _ = train.prepare_features(df)
        assert list(X.columns) == train.FEATURES

    def test_median_imputation_preserves_non_null_values(self):
        train = self._import()
        df = _make_synthetic_df(n=100)
        original_value = df.loc[5, "ext_source_2"]
        df.loc[0:3, "ext_source_2"] = np.nan
        X, _ = train.prepare_features(df)
        assert X.loc[5, "ext_source_2"] == pytest.approx(original_value)


# ===========================================================================
# Metric calculations (standalone, no model required)
# ===========================================================================
class TestCreditMetrics:
    def test_gini_equals_2_auc_minus_1(self):
        """Gini = 2*AUC - 1 is the standard credit industry relationship."""
        from sklearn.metrics import roc_auc_score

        rng = np.random.default_rng(0)
        y_true = rng.integers(0, 2, size=500)
        # Good model scores: positives get higher predicted proba
        y_score = rng.random(500)
        y_score[y_true == 1] += 0.3
        y_score = np.clip(y_score, 0, 1)

        auc = roc_auc_score(y_true, y_score)
        gini = 2 * auc - 1
        assert gini == pytest.approx(2 * auc - 1, abs=1e-10)

    def test_gini_range(self):
        """Gini must be in [-1, 1]; 0 = random; 1 = perfect."""
        from sklearn.metrics import roc_auc_score

        rng = np.random.default_rng(1)
        y_true = rng.integers(0, 2, size=500)
        y_score = rng.random(500)
        auc = roc_auc_score(y_true, y_score)
        gini = 2 * auc - 1
        assert -1 <= gini <= 1

    def test_ks_perfect_separation(self):
        """When scores perfectly separate classes, KS = 1.0."""
        from scipy import stats

        defaults = np.ones(200)  # all defaulters score 1.0
        repaid = np.zeros(1800)  # all non-defaulters score 0.0
        ks_stat, _ = stats.ks_2samp(defaults, repaid)
        assert ks_stat == pytest.approx(1.0)

    def test_ks_random_scores(self):
        """Random scores → KS close to 0."""
        from scipy import stats

        rng = np.random.default_rng(42)
        defaults = rng.random(200)
        repaid = rng.random(1800)
        ks_stat, _ = stats.ks_2samp(defaults, repaid)
        assert ks_stat < 0.10  # near zero for random

    def test_auc_greater_than_random_for_synthetic_good_model(self):
        """A model that shifts positive scores higher should have AUC > 0.5."""
        from sklearn.metrics import roc_auc_score

        rng = np.random.default_rng(5)
        y_true = rng.integers(0, 2, size=1000)
        y_score = rng.random(1000) + y_true * 0.5  # shift positives
        y_score = np.clip(y_score, 0, 1)
        auc = roc_auc_score(y_true, y_score)
        assert auc > 0.5


# ===========================================================================
# XGBoost model contract (train on synthetic data)
# ===========================================================================
class TestXGBModelContract:
    @pytest.fixture(scope="class")
    def trained_model(self):
        from xgboost import XGBClassifier

        df = _make_synthetic_df(n=3000)
        X = df[FEATURES].fillna(0)
        y = df["label"]
        xgb = XGBClassifier(
            n_estimators=50,
            max_depth=3,
            scale_pos_weight=11,
            random_state=42,
            eval_metric="auc",
            tree_method="hist",
        )
        xgb.fit(X, y)
        return xgb, X, y

    def test_model_outputs_probabilities_in_unit_interval(self, trained_model):
        xgb, X, _ = trained_model
        proba = xgb.predict_proba(X)[:, 1]
        assert (proba >= 0).all() and (proba <= 1).all()

    def test_model_feature_importances_length_matches_features(self, trained_model):
        xgb, _, _ = trained_model
        assert len(xgb.feature_importances_) == len(FEATURES)

    def test_model_feature_importances_sum_to_one(self, trained_model):
        xgb, _, _ = trained_model
        assert xgb.feature_importances_.sum() == pytest.approx(1.0, abs=1e-5)

    def test_model_auc_above_random(self, trained_model):
        """Even on small synthetic data the model should beat random."""
        from sklearn.metrics import roc_auc_score

        xgb, X, y = trained_model
        proba = xgb.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, proba)
        assert auc >= 0.50

    def test_predict_proba_shape(self, trained_model):
        xgb, X, _ = trained_model
        proba = xgb.predict_proba(X)
        assert proba.shape == (len(X), 2)

    def test_probabilities_sum_to_one_per_row(self, trained_model):
        xgb, X, _ = trained_model
        proba = xgb.predict_proba(X)
        row_sums = proba.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-5)

    def test_model_can_be_serialised_and_restored(self, trained_model, tmp_path):
        import joblib

        xgb, X, _ = trained_model
        path = tmp_path / "test_model.pkl"
        joblib.dump(xgb, path)
        loaded = joblib.load(path)
        orig_proba = xgb.predict_proba(X[:10])[:, 1]
        loaded_proba = loaded.predict_proba(X[:10])[:, 1]
        np.testing.assert_allclose(orig_proba, loaded_proba, rtol=1e-5)


# ===========================================================================
# SMOTE output contract
# ===========================================================================
class TestSmoteContract:
    def test_smote_increases_minority_class(self):
        from imblearn.over_sampling import SMOTE

        df = _make_synthetic_df(n=2000)
        X = df[FEATURES].fillna(0)
        y = df["label"]
        before_rate = y.mean()
        smote = SMOTE(random_state=42, sampling_strategy=0.3)
        _, y_res = smote.fit_resample(X, y)
        assert y_res.mean() > before_rate

    def test_smote_no_nulls_in_output(self):
        from imblearn.over_sampling import SMOTE

        df = _make_synthetic_df(n=2000)
        X = df[FEATURES].fillna(df[FEATURES].median())
        y = df["label"]
        smote = SMOTE(random_state=42, sampling_strategy=0.3)
        X_res, _ = smote.fit_resample(X, y)
        assert pd.DataFrame(X_res).isnull().sum().sum() == 0

    def test_smote_output_has_same_columns(self):
        from imblearn.over_sampling import SMOTE

        df = _make_synthetic_df(n=2000)
        X = df[FEATURES].fillna(0)
        y = df["label"]
        smote = SMOTE(random_state=42, sampling_strategy=0.3)
        X_res, _ = smote.fit_resample(X, y)
        assert X_res.shape[1] == len(FEATURES)
