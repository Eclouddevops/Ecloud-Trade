"""
News Sentiment Analysis Module
Scrapes financial news and performs sentiment analysis for Indian stocks.
"""
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from datetime import datetime
import re


class NewsSentimentAnalyzer:
    """Analyzes news sentiment for Indian stocks."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def get_news_sentiment(self, symbol: str) -> dict:
        """
        Get aggregated news sentiment for a stock.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')

        Returns:
            Dictionary with sentiment scores and news headlines
        """
        headlines = self._fetch_google_news(symbol)

        if not headlines:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "news_count": 0,
                "headlines": [],
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }

        sentiments = []
        analyzed_headlines = []

        for headline in headlines[:15]:  # Analyze top 15 headlines
            blob = TextBlob(headline)
            polarity = blob.sentiment.polarity

            label = "Neutral"
            if polarity > 0.1:
                label = "Positive"
            elif polarity < -0.1:
                label = "Negative"

            sentiments.append(polarity)
            analyzed_headlines.append(
                {"headline": headline, "sentiment": polarity, "label": label}
            )

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        positive_count = sum(1 for s in sentiments if s > 0.1)
        negative_count = sum(1 for s in sentiments if s < -0.1)
        neutral_count = len(sentiments) - positive_count - negative_count

        overall_label = "Neutral"
        if avg_sentiment > 0.1:
            overall_label = "Positive"
        elif avg_sentiment < -0.1:
            overall_label = "Negative"

        return {
            "sentiment_score": round(avg_sentiment, 4),
            "sentiment_label": overall_label,
            "news_count": len(analyzed_headlines),
            "headlines": analyzed_headlines[:5],  # Return top 5
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
        }

    def _fetch_google_news(self, symbol: str) -> list:
        """
        Fetch news headlines from Google News for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            List of headline strings
        """
        query = f"{symbol} NSE stock India"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.find_all("item")

            headlines = []
            for item in items[:20]:
                title = item.find("title")
                if title:
                    # Clean the headline
                    text = title.get_text()
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        headlines.append(text)

            return headlines

        except Exception as e:
            print(f"Warning: Could not fetch news for {symbol}: {e}")
            return []

    def get_market_mood(self) -> dict:
        """
        Get overall market mood based on market news.

        Returns:
            Dictionary with market mood assessment
        """
        headlines = self._fetch_google_news("NIFTY 50 Indian stock market")

        if not headlines:
            return {"mood": "Neutral", "score": 0.0}

        sentiments = [TextBlob(h).sentiment.polarity for h in headlines[:10]]
        avg = sum(sentiments) / len(sentiments) if sentiments else 0.0

        mood = "Neutral"
        if avg > 0.15:
            mood = "Bullish"
        elif avg < -0.15:
            mood = "Bearish"

        return {"mood": mood, "score": round(avg, 4)}
