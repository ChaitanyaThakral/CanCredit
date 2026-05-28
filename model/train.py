"""
model/train.py — Standalone credit risk model training script.
Mirrors the logic in notebooks/01_credit_risk_eda_and_model.ipynb
but runs headlessly (no plots shown, only saved).

Usage:
    python model/train.py
"""
import os
import json
import warnings
import joblib
import pathlib

import snowflake.connector
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # headless mode
import matplotlib.pyplot as plt

import mlflow
import mlflow.sklearn
import shap

from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
from scipy import stats

warnings.filterwarnings('ignore')

# ── Directory setup ───────────────────────────────────────────────────────
REPORTS_DIR = pathlib.Path(__file__).parent.parent / 'reports'
MODEL_DIR   = pathlib.Path(__file__).parent
REPORTS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# ── Feature list ──────────────────────────────────────────────────────────
FEATURES = [
    'ext_source_1', 'ext_source_2', 'ext_source_3',
    'credit_to_income_ratio', 'annuity_to_income_ratio',
    'bureau_delinquency_rate', 'bureau_worst_delinquency',
    'bureau_total_overdue', 'inst_late_rate', 'inst_max_days_late',
    'inst_avg_payment_ratio', 'cc_avg_utilization',
    'cc_months_overdue', 'prev_refusal_rate',
    'prev_num_applications', 'age_years', 'years_employed',
    'composite_risk_score',
]

XGB_PARAMS = {
    'n_estimators': 500,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'scale_pos_weight': 11,
    'eval_metric': 'auc',
    'random_state': 42,
    'n_jobs': -1,
    'tree_method': 'hist',
}


def load_data() -> pd.DataFrame:
    """Load ML feature store from Snowflake."""
    conn = snowflake.connector.connect(
        account=os.environ['SNOWFLAKE_ACCOUNT'],
        user=os.environ['SNOWFLAKE_USER'],
        password=os.environ['SNOWFLAKE_PASSWORD'],
        database='CANCREDIT_DB',
        warehouse='CANCREDIT_WH',
    )
    df = pd.read_sql(
        "SELECT * FROM CANCREDIT_DB.ML_FEATURES.ML_FEATURES_TRAINING", conn
    )
    conn.close()
    df.columns = df.columns.str.lower()
    print(f"Loaded {df.shape[0]:,} rows × {df.shape[1]} cols | "
          f"Default rate: {df['label'].mean():.3%}")
    return df


def prepare_features(df: pd.DataFrame):
    """Return X, y with median imputation."""
    X = df[FEATURES].fillna(df[FEATURES].median())
    y = df['label']
    return X, y


def train_and_evaluate(X, y):
    """Train LR baseline + XGBoost, log to MLflow, save artifacts."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    mlflow.set_tracking_uri('file:///cancredit_mlflow')
    mlflow.set_experiment('cancredit_credit_risk')

    # ── LR baseline ───────────────────────────────────────────────────────
    smote = SMOTE(random_state=42, sampling_strategy=0.3)
    X_res, y_res = smote.fit_resample(X, y)

    with mlflow.start_run(run_name='logistic_regression_baseline'):
        mlflow.log_param('model_type', 'LogisticRegression')
        mlflow.log_param('class_balance', 'SMOTE_0.3')
        mlflow.log_param('features', len(FEATURES))
        lr_pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('model', LogisticRegression(C=1.0, max_iter=1000, random_state=42))
        ])
        lr_scores = cross_val_score(lr_pipe, X_res, y_res, cv=cv, scoring='roc_auc')
        mlflow.log_metric('cv_auc_mean', round(float(lr_scores.mean()), 6))
        mlflow.log_metric('cv_auc_std',  round(float(lr_scores.std()), 6))
        mlflow.log_metric('gini', round(float(2 * lr_scores.mean() - 1), 6))
        print(f"LR    │ AUC: {lr_scores.mean():.4f} ± {lr_scores.std():.4f} "
              f"│ Gini: {2*lr_scores.mean()-1:.4f}")

    # ── XGBoost ───────────────────────────────────────────────────────────
    with mlflow.start_run(run_name='xgboost_tuned'):
        mlflow.log_params(XGB_PARAMS)
        mlflow.log_param('model_type', 'XGBoostClassifier')
        mlflow.log_param('class_balance', 'scale_pos_weight_11')
        xgb = XGBClassifier(**XGB_PARAMS)
        xgb_cv = cross_val_score(xgb, X, y, cv=cv, scoring='roc_auc')
        mlflow.log_metric('cv_auc_mean', round(float(xgb_cv.mean()), 6))
        mlflow.log_metric('cv_auc_std',  round(float(xgb_cv.std()), 6))
        mlflow.log_metric('gini', round(float(2 * xgb_cv.mean() - 1), 6))
        print(f"XGB   │ AUC: {xgb_cv.mean():.4f} ± {xgb_cv.std():.4f} "
              f"│ Gini: {2*xgb_cv.mean()-1:.4f}")

        # Final fit + artifact logging
        xgb.fit(X, y)
        mlflow.sklearn.log_model(xgb, 'xgb_credit_model',
                                 registered_model_name='cancredit_xgb_v1')
        fi = dict(zip(FEATURES, xgb.feature_importances_.tolist()))
        fi_path = '/tmp/feature_importances.json'
        with open(fi_path, 'w') as f:
            json.dump(dict(sorted(fi.items(), key=lambda x: x[1], reverse=True)), f, indent=2)
        mlflow.log_artifact(fi_path)
        joblib.dump(xgb, MODEL_DIR / 'xgb_credit_model.pkl')
        print(f"✅ Model saved → {MODEL_DIR / 'xgb_credit_model.pkl'}")

    return xgb


def evaluate_and_plot(xgb, X, y):
    """Held-out evaluation + ROC plot + SHAP plots."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    xgb_eval = XGBClassifier(**XGB_PARAMS)
    xgb_eval.fit(X_train, y_train)
    y_proba = xgb_eval.predict_proba(X_test)[:, 1]

    auc  = roc_auc_score(y_test, y_proba)
    gini = 2 * auc - 1
    ks_stat, _ = stats.ks_2samp(y_proba[y_test == 1], y_proba[y_test == 0])

    print("\n══════════════════════════════════════")
    print(" CanCredit XGBoost — Held-out Results")
    print("══════════════════════════════════════")
    print(f"  AUC-ROC:          {auc:.4f}  {'✅' if auc > 0.70 else '❌'}")
    print(f"  Gini Coefficient: {gini:.4f}  {'✅' if gini > 0.35 else '❌'}")
    print(f"  KS Statistic:     {ks_stat:.4f}  {'✅' if ks_stat > 0.30 else '❌'}")

    # ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color='crimson', lw=2.5,
            label=f'XGBoost (AUC={auc:.3f}, Gini={gini:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', lw=1.2)
    ax.fill_between(fpr, tpr, alpha=0.08, color='crimson')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve — CanCredit XGBoost')
    ax.legend()
    ax.annotate(f'KS = {ks_stat:.3f}', xy=(0.6, 0.4), fontsize=11,
                bbox=dict(boxstyle='round', facecolor='lightyellow'))
    fig.savefig(REPORTS_DIR / 'roc_curve.png', dpi=150, bbox_inches='tight')
    plt.close()

    # SHAP
    explainer = shap.TreeExplainer(xgb_eval)
    X_sample  = X_test.sample(min(2000, len(X_test)), random_state=42)
    shap_vals = explainer.shap_values(X_sample)

    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_vals, X_sample, feature_names=FEATURES,
                      plot_type='bar', show=False)
    plt.title('SHAP Feature Importance — Global')
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / 'shap_importance.png', dpi=150, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_vals, X_sample, feature_names=FEATURES, show=False)
    plt.title('SHAP Beeswarm — Direction of Effect')
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / 'shap_beeswarm.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ Plots saved to {REPORTS_DIR}")


if __name__ == '__main__':
    df  = load_data()
    X, y = prepare_features(df)
    xgb = train_and_evaluate(X, y)
    evaluate_and_plot(xgb, X, y)
