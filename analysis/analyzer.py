"""
Stock Analysis Engine
Combines all components to produce comprehensive stock analysis and trading signals.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from data.data_collector import MarketDataCollector
from data.news_sentiment import NewsSentimentAnalyzer
from indicators.technical import TechnicalIndicators
from models.feature_engineering import FeatureEngineer
from models.predictor import StockPredictor
from config.settings import (
    PREDICTION_HORIZONS,
    STOP_LOSS_MULTIPLIER,
    TARGET_RISK_REWARD,
)


class StockAnalyzer:
    """
    Complete stock analysis engine.
    Combines data collection, technical analysis, ML prediction, and news sentiment.
    """

    def __init__(self):
        self.data_collector = MarketDataCollector()
        self.news_analyzer = NewsSentimentAnalyzer()
        self.predictor = StockPredictor()

    def analyze(self, symbol: str, train_model: bool = True) -> dict:
        """
        Perform complete analysis on a stock.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            train_model: Whether to train ML models (set False if already trained)

        Returns:
            Complete analysis dictionary in JSON-compatible format
        """
        print(f"\n{'='*60}")
        print(f"  Analyzing: {symbol}")
        print(f"{'='*60}")

        # Step 1: Collect Data
        print("\n[1/6] Collecting market data...")
        df = self.data_collector.get_stock_data(symbol)
        current_info = self.data_collector.get_current_price(symbol)
        current_price = current_info.get("current_price") or df["close"].iloc[-1]

        # Step 2: Calculate Technical Indicators
        print("[2/6] Calculating technical indicators...")
        tech = TechnicalIndicators(df)
        df_with_indicators = tech.calculate_all()
        indicator_summary = tech.get_indicator_summary()
        support_resistance = tech.get_support_resistance()

        # Step 3: Feature Engineering & ML Prediction
        print("[3/6] Engineering features & training models...")
        predictions = {}
        if train_model:
            for horizon_name, horizon_days in PREDICTION_HORIZONS.items():
                fe = FeatureEngineer(df_with_indicators.copy())
                X, y = fe.create_features(horizon=horizon_days)

                if len(X) > 50:  # Need minimum data
                    self.predictor.train(X, y, symbol, horizon_name)

            # Get predictions using latest features
            fe_latest = FeatureEngineer(df_with_indicators.copy())
            X_latest, _ = fe_latest.create_features(horizon=1)
            latest_features = X_latest.iloc[[-1]]

            predictions = self.predictor.predict_all_horizons(latest_features, symbol)
        else:
            fe_latest = FeatureEngineer(df_with_indicators.copy())
            X_latest, _ = fe_latest.create_features(horizon=1)
            latest_features = X_latest.iloc[[-1]]
            predictions = self.predictor.predict_all_horizons(latest_features, symbol)

        # Step 4: News Sentiment
        print("[4/6] Analyzing news sentiment...")
        sentiment = self.news_analyzer.get_news_sentiment(symbol)

        # Step 5: Market Context
        print("[5/6] Checking market context...")
        market_mood = self.news_analyzer.get_market_mood()
        nifty_trend = self._get_nifty_trend()

        # Step 6: Generate Trading Signal
        print("[6/6] Generating trading signal...")
        signal = self._generate_signal(
            current_price, indicator_summary, predictions, sentiment, support_resistance, df_with_indicators
        )

        # Compile final analysis
        analysis = {
            "symbol": symbol,
            "analysis_timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "stock_info": {
                "sector": current_info.get("sector"),
                "market_cap": current_info.get("market_cap"),
                "pe_ratio": current_info.get("pe_ratio"),
                "52_week_high": current_info.get("52_week_high"),
                "52_week_low": current_info.get("52_week_low"),
            },
            "trend_analysis": signal["trend"],
            "recommendation": signal["recommendation"],
            "entry_price": signal["entry_price"],
            "stop_loss": signal["stop_loss"],
            "target_price": signal["target_price"],
            "risk_level": signal["risk_level"],
            "technical_indicators": indicator_summary,
            "support_resistance": support_resistance,
            "predictions": {
                "1_day": {
                    "direction": predictions.get("1_day", {}).get("prediction", "N/A"),
                    "probability_up": predictions.get("1_day", {}).get(
                        "ensemble_probability", 0.5
                    ),
                    "confidence": predictions.get("1_day", {}).get("confidence", 0.0),
                },
                "1_week": {
                    "direction": predictions.get("1_week", {}).get("prediction", "N/A"),
                    "probability_up": predictions.get("1_week", {}).get(
                        "ensemble_probability", 0.5
                    ),
                    "confidence": predictions.get("1_week", {}).get("confidence", 0.0),
                },
                "1_month": {
                    "direction": predictions.get("1_month", {}).get("prediction", "N/A"),
                    "probability_up": predictions.get("1_month", {}).get(
                        "ensemble_probability", 0.5
                    ),
                    "confidence": predictions.get("1_month", {}).get("confidence", 0.0),
                },
            },
            "news_sentiment": {
                "overall_sentiment": sentiment["sentiment_label"],
                "sentiment_score": sentiment["sentiment_score"],
                "positive_news": sentiment["positive_count"],
                "negative_news": sentiment["negative_count"],
                "top_headlines": [
                    h["headline"] for h in sentiment.get("headlines", [])[:3]
                ],
            },
            "market_context": {
                "nifty_trend": nifty_trend,
                "market_mood": market_mood["mood"],
            },
            "reasoning": signal["reasoning"],
        }

        print(f"\n✓ Analysis complete for {symbol}")
        return analysis

    def _generate_signal(
        self,
        current_price: float,
        indicators: dict,
        predictions: dict,
        sentiment: dict,
        support_resistance: dict,
        df: pd.DataFrame,
    ) -> dict:
        """Generate trading signal based on all available data."""
        score = 0  # -10 to +10 scale

        # Technical Indicator Scoring
        # RSI
        if indicators["rsi"] < 30:
            score += 2  # Oversold = bullish
        elif indicators["rsi"] > 70:
            score -= 2  # Overbought = bearish
        elif indicators["rsi"] < 50:
            score -= 0.5
        else:
            score += 0.5

        # MACD
        if "Bullish" in indicators["macd_signal"]:
            score += 1.5
        elif "Bearish" in indicators["macd_signal"]:
            score -= 1.5

        # Moving Averages
        if "Strong Bullish" in indicators["ma_signal"]:
            score += 2
        elif "Bullish" in indicators["ma_signal"]:
            score += 1
        elif "Strong Bearish" in indicators["ma_signal"]:
            score -= 2
        elif "Bearish" in indicators["ma_signal"]:
            score -= 1

        # Bollinger Bands
        if indicators["bb_signal"] == "Oversold":
            score += 1
        elif indicators["bb_signal"] == "Overbought":
            score -= 1

        # ML Predictions
        day_pred = predictions.get("1_day", {})
        week_pred = predictions.get("1_week", {})
        if day_pred.get("prediction") == "UP":
            score += 1
        elif day_pred.get("prediction") == "DOWN":
            score -= 1
        if week_pred.get("prediction") == "UP":
            score += 1
        elif week_pred.get("prediction") == "DOWN":
            score -= 1

        # News Sentiment
        if sentiment["sentiment_label"] == "Positive":
            score += 1
        elif sentiment["sentiment_label"] == "Negative":
            score -= 1

        # Determine trend
        if score >= 3:
            trend = "Bullish"
        elif score <= -3:
            trend = "Bearish"
        else:
            trend = "Sideways"

        # Determine recommendation
        if score >= 4:
            recommendation = "STRONG BUY"
        elif score >= 2:
            recommendation = "BUY"
        elif score <= -4:
            recommendation = "STRONG SELL"
        elif score <= -2:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        # Calculate entry, stop loss, target
        atr = indicators["atr"]
        if "BUY" in recommendation:
            entry_price = round(current_price, 2)
            stop_loss = round(current_price - (atr * STOP_LOSS_MULTIPLIER), 2)
            target_price = round(
                current_price + (atr * STOP_LOSS_MULTIPLIER * TARGET_RISK_REWARD), 2
            )
        elif "SELL" in recommendation:
            entry_price = round(current_price, 2)
            stop_loss = round(current_price + (atr * STOP_LOSS_MULTIPLIER), 2)
            target_price = round(
                current_price - (atr * STOP_LOSS_MULTIPLIER * TARGET_RISK_REWARD), 2
            )
        else:
            entry_price = round(current_price, 2)
            stop_loss = round(current_price - (atr * STOP_LOSS_MULTIPLIER), 2)
            target_price = round(current_price + (atr * STOP_LOSS_MULTIPLIER), 2)

        # Risk Level
        volatility = indicators.get("atr", 0) / current_price * 100
        if volatility > 3:
            risk_level = "High"
        elif volatility > 1.5:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Generate reasoning
        reasoning = self._build_reasoning(
            trend, indicators, predictions, sentiment, score
        )

        return {
            "trend": trend,
            "recommendation": recommendation,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "risk_level": risk_level,
            "score": round(score, 2),
            "reasoning": reasoning,
        }

    def _build_reasoning(
        self, trend: str, indicators: dict, predictions: dict, sentiment: dict, score: float
    ) -> str:
        """Build human-readable reasoning for the recommendation."""
        parts = []

        parts.append(f"Overall trend is {trend} with a composite score of {score:.1f}/10.")

        # RSI
        parts.append(
            f"RSI at {indicators['rsi']} indicates {indicators['rsi_signal'].lower()} conditions."
        )

        # MACD
        parts.append(f"MACD shows {indicators['macd_signal'].lower()} momentum.")

        # Moving Averages
        parts.append(f"Moving average analysis: {indicators['ma_signal']}.")

        # ADX
        parts.append(
            f"Trend strength (ADX): {indicators['adx']} ({indicators['trend_strength']})."
        )

        # ML Prediction
        day_prob = predictions.get("1_day", {}).get("ensemble_probability", 0.5)
        parts.append(
            f"ML model predicts {day_prob*100:.1f}% probability of price increase tomorrow."
        )

        # Sentiment
        parts.append(f"News sentiment is {sentiment['sentiment_label'].lower()}.")

        return " ".join(parts)

    def _get_nifty_trend(self) -> str:
        """Determine NIFTY 50 trend."""
        try:
            nifty_df = self.data_collector.get_nifty50_data(period="3mo")
            if len(nifty_df) < 50:
                return "Unknown"

            sma_20 = nifty_df["close"].rolling(20).mean().iloc[-1]
            sma_50 = nifty_df["close"].rolling(50).mean().iloc[-1]
            current = nifty_df["close"].iloc[-1]

            if current > sma_20 > sma_50:
                return "Bullish"
            elif current < sma_20 < sma_50:
                return "Bearish"
            else:
                return "Sideways"
        except Exception:
            return "Unknown"
