"""
News Intelligence Module
Fetches and analyzes market news with sentiment scoring.
"""
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from datetime import datetime


class NewsIntelligence:
    """Fetches market news and performs sentiment analysis."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })

    def get_company_news(self, symbol: str) -> list:
        """Get latest news for a company with sentiment."""
        headlines = self._fetch_news(f"{symbol} NSE stock")
        return self._analyze_headlines(headlines)

    def get_market_news(self) -> list:
        """Get general Indian market news."""
        headlines = self._fetch_news("Indian stock market NIFTY today")
        return self._analyze_headlines(headlines)

    def get_government_news(self) -> list:
        """Get RBI, budget, policy news."""
        headlines = self._fetch_news("RBI policy India budget GST reform")
        return self._analyze_headlines(headlines)

    def get_international_news(self) -> list:
        """Get international market impact news."""
        headlines = self._fetch_news("US FED crude oil gold dollar global market")
        return self._analyze_headlines(headlines)

    def get_full_news_report(self, symbol: str = None) -> dict:
        """Get comprehensive news report."""
        report = {
            "market_news": self.get_market_news()[:5],
            "government_news": self.get_government_news()[:5],
            "international_news": self.get_international_news()[:5],
        }
        if symbol:
            report["company_news"] = self.get_company_news(symbol)[:5]

        # Overall sentiment
        all_sentiments = []
        for key in report:
            for item in report[key]:
                all_sentiments.append(item["score"])

        avg = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0
        positive = sum(1 for s in all_sentiments if s > 0.1)
        negative = sum(1 for s in all_sentiments if s < -0.1)
        neutral = len(all_sentiments) - positive - negative

        report["overall"] = {
            "score": round(avg, 4),
            "positive_pct": round(positive / max(len(all_sentiments), 1) * 100),
            "negative_pct": round(negative / max(len(all_sentiments), 1) * 100),
            "neutral_pct": round(neutral / max(len(all_sentiments), 1) * 100),
            "impact": "Bullish" if avg > 0.1 else "Bearish" if avg < -0.1 else "Neutral",
            "impact_score": round(avg * 10, 1),  # -10 to +10 scale
        }
        return report

    def _fetch_news(self, query: str) -> list:
        """Fetch news from Google News RSS."""
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "html.parser")
            items = soup.find_all("item")
            headlines = []
            for item in items[:15]:
                title = item.find("title")
                pub_date = item.find("pubdate")
                if title:
                    headlines.append({
                        "text": title.get_text().strip(),
                        "date": pub_date.get_text().strip() if pub_date else "",
                    })
            return headlines
        except Exception:
            return []

    def _analyze_headlines(self, headlines: list) -> list:
        """Analyze sentiment of headlines."""
        results = []
        for h in headlines:
            blob = TextBlob(h["text"])
            score = blob.sentiment.polarity
            sentiment = "Positive" if score > 0.1 else "Negative" if score < -0.1 else "Neutral"
            impact = "Bullish" if score > 0.1 else "Bearish" if score < -0.1 else "Neutral"
            results.append({
                "headline": h["text"],
                "date": h.get("date", ""),
                "score": round(score, 4),
                "sentiment": sentiment,
                "impact": impact,
            })
        return results
