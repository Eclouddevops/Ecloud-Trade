"""
ML Prediction Module
Trains and uses XGBoost and Random Forest models for stock price prediction.
"""
import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from config.settings import (
    TRAIN_TEST_SPLIT,
    RANDOM_STATE,
    XGBOOST_PARAMS,
    RANDOM_FOREST_PARAMS,
    MODEL_SAVE_DIR,
    PREDICTION_HORIZONS,
)


class StockPredictor:
    """ML-based stock price direction predictor."""

    def __init__(self):
        self.models = {}
        self.feature_importance = {}
        os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

    def train(self, X: pd.DataFrame, y: pd.Series, symbol: str, horizon: str = "1_day"):
        """
        Train both XGBoost and Random Forest models.

        Args:
            X: Feature matrix
            y: Target variable (1=up, 0=down)
            symbol: Stock symbol for model saving
            horizon: Prediction horizon name
        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=1 - TRAIN_TEST_SPLIT, random_state=RANDOM_STATE, shuffle=False
        )

        # Train XGBoost
        xgb_model = XGBClassifier(**XGBOOST_PARAMS, use_label_encoder=False, eval_metric="logloss")
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict(X_test)
        xgb_accuracy = accuracy_score(y_test, xgb_pred)

        # Train Random Forest
        rf_model = RandomForestClassifier(**RANDOM_FOREST_PARAMS)
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        rf_accuracy = accuracy_score(y_test, rf_pred)

        # Store models
        model_key = f"{symbol}_{horizon}"
        self.models[model_key] = {
            "xgboost": {"model": xgb_model, "accuracy": xgb_accuracy},
            "random_forest": {"model": rf_model, "accuracy": rf_accuracy},
        }

        # Feature importance from XGBoost
        importance = pd.Series(
            xgb_model.feature_importances_, index=X.columns
        ).sort_values(ascending=False)
        self.feature_importance[model_key] = importance.head(15).to_dict()

        # Save models
        self._save_model(xgb_model, f"{symbol}_{horizon}_xgb.pkl")
        self._save_model(rf_model, f"{symbol}_{horizon}_rf.pkl")

        print(f"  XGBoost Accuracy ({horizon}): {xgb_accuracy:.4f}")
        print(f"  Random Forest Accuracy ({horizon}): {rf_accuracy:.4f}")

        return {
            "xgboost_accuracy": round(xgb_accuracy, 4),
            "random_forest_accuracy": round(rf_accuracy, 4),
        }

    def predict(self, X: pd.DataFrame, symbol: str, horizon: str = "1_day") -> dict:
        """
        Make prediction using trained models.

        Args:
            X: Feature row(s) for prediction
            symbol: Stock symbol
            horizon: Prediction horizon

        Returns:
            Dictionary with prediction probabilities
        """
        model_key = f"{symbol}_{horizon}"

        if model_key not in self.models:
            # Try loading saved models
            xgb_path = os.path.join(MODEL_SAVE_DIR, f"{symbol}_{horizon}_xgb.pkl")
            rf_path = os.path.join(MODEL_SAVE_DIR, f"{symbol}_{horizon}_rf.pkl")

            if os.path.exists(xgb_path) and os.path.exists(rf_path):
                self.models[model_key] = {
                    "xgboost": {"model": joblib.load(xgb_path), "accuracy": None},
                    "random_forest": {"model": joblib.load(rf_path), "accuracy": None},
                }
            else:
                raise ValueError(
                    f"No trained model found for {symbol} ({horizon}). Train first."
                )

        models = self.models[model_key]

        # XGBoost prediction
        xgb_proba = models["xgboost"]["model"].predict_proba(X)[0]
        xgb_up_prob = xgb_proba[1] if len(xgb_proba) > 1 else xgb_proba[0]

        # Random Forest prediction
        rf_proba = models["random_forest"]["model"].predict_proba(X)[0]
        rf_up_prob = rf_proba[1] if len(rf_proba) > 1 else rf_proba[0]

        # Ensemble (weighted average - XGBoost gets more weight)
        ensemble_prob = 0.6 * xgb_up_prob + 0.4 * rf_up_prob

        return {
            "xgboost_probability": round(float(xgb_up_prob), 4),
            "random_forest_probability": round(float(rf_up_prob), 4),
            "ensemble_probability": round(float(ensemble_prob), 4),
            "prediction": "UP" if ensemble_prob > 0.5 else "DOWN",
            "confidence": round(abs(ensemble_prob - 0.5) * 2, 4),  # 0 to 1 scale
        }

    def predict_all_horizons(self, X: pd.DataFrame, symbol: str) -> dict:
        """
        Make predictions for all time horizons.

        Args:
            X: Feature row for prediction
            symbol: Stock symbol

        Returns:
            Dictionary with predictions for each horizon
        """
        predictions = {}
        for horizon_name in PREDICTION_HORIZONS.keys():
            try:
                predictions[horizon_name] = self.predict(X, symbol, horizon_name)
            except ValueError:
                predictions[horizon_name] = {
                    "prediction": "N/A",
                    "ensemble_probability": 0.5,
                    "confidence": 0.0,
                    "error": "Model not trained for this horizon",
                }
        return predictions

    def _save_model(self, model, filename: str):
        """Save model to disk."""
        path = os.path.join(MODEL_SAVE_DIR, filename)
        joblib.dump(model, path)

    def get_feature_importance(self, symbol: str, horizon: str = "1_day") -> dict:
        """Get feature importance for a trained model."""
        model_key = f"{symbol}_{horizon}"
        return self.feature_importance.get(model_key, {})
