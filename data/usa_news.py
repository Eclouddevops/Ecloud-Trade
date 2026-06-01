"""
USA News & Political Sentiment Module
Fetches US political news (President, Fed, trade policy) and economic news
that impacts Indian markets. Analyzes sentiment to adjust trading signals.
"""
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from textblob import TextBlob
from datetime import datetime
import re
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class USANewsAnalyzer:
    """Fetches and analyzes USA political/economic news impacting Indian markets."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def get_usa_news(self) -> dict:
        """
        Get comprehensive USA news covering president, economy, and markets.

        Returns:
            Dictionary with categorized USA news and sentiment analysis
        """
        president_news = self._fetch_news("US President policy economy")
        fed_news = self._fetch_news("Federal Reserve interest rate decision")
        trade_news = self._fetch_news("US India trade tariff policy")
        market_news = self._fetch_news("US stock market Wall Street today")

        all_headlines = {
            "president": president_news,
            "federal_reserve": fed_news,
            "trade_policy": trade_news,
            "us_markets": market_news,
        }

        # Analyze sentiment for each category
        category_sentiments = {}
        all_analyzed = []

        for category, headlines in all_headlines.items():
            if not headlines:
                category_sentiments[category] = {
                    "sentiment": "Neutral",
                    "score": 0.0,
                    "headlines": [],
                }
                continue

            sentiments = []
            analyzed = []
            for headline in headlines[:8]:
                blob = TextBlob(headline)
                polarity = blob.sentiment.polarity
                label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                sentiments.append(polarity)
                analyzed.append({"headline": headline, "sentiment": polarity, "label": label})

            avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
            overall = "Positive" if avg > 0.1 else "Negative" if avg < -0.1 else "Neutral"

            category_sentiments[category] = {
                "sentiment": overall,
                "score": round(avg, 4),
                "headlines": analyzed[:4],
            }
            all_analyzed.extend(analyzed)

        # Overall USA sentiment impact on Indian markets
        all_scores = [cs["score"] for cs in category_sentiments.values()]
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Determine impact on Indian market
        if overall_score > 0.15:
            india_impact = "Positive"
            impact_description = "US news is favorable — likely positive for Indian markets"
        elif overall_score < -0.15:
            india_impact = "Negative"
            impact_description = "US news is unfavorable — may create selling pressure in Indian markets"
        else:
            india_impact = "Neutral"
            impact_description = "US news is mixed — limited direct impact expected on Indian markets"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_sentiment": "Positive" if overall_score > 0.1 else "Negative" if overall_score < -0.1 else "Neutral",
            "overall_score": round(overall_score, 4),
            "india_market_impact": india_impact,
            "impact_description": impact_description,
            "categories": category_sentiments,
            "top_headlines": [h["headline"] for h in all_analyzed[:6]],
        }

    def get_president_news(self) -> dict:
        """
        Get news specifically about the US President and policy decisions.

        Returns:
            Dictionary with president-related news and market impact
        """
        headlines = self._fetch_news("US President executive order economy trade")
        tariff_headlines = self._fetch_news("US President tariff India trade deal")

        all_headlines = headlines + tariff_headlines
        if not all_headlines:
            return {
                "sentiment": "Neutral",
                "score": 0.0,
                "headlines": [],
                "market_impact": "No significant presidential news affecting markets",
            }

        sentiments = []
        analyzed = []
        for headline in all_headlines[:12]:
            blob = TextBlob(headline)
            polarity = blob.sentiment.polarity
            label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
            sentiments.append(polarity)
            analyzed.append({"headline": headline, "sentiment": polarity, "label": label})

        avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
        overall = "Positive" if avg > 0.1 else "Negative" if avg < -0.1 else "Neutral"

        # Determine market impact
        if avg > 0.2:
            impact = "Strong positive — pro-business policies may boost FII inflows to India"
        elif avg > 0.05:
            impact = "Mildly positive — stable US policy supports global risk appetite"
        elif avg < -0.2:
            impact = "Strong negative — trade tensions or policy uncertainty may hurt Indian markets"
        elif avg < -0.05:
            impact = "Mildly negative — some caution warranted for export-heavy stocks"
        else:
            impact = "Neutral — no significant policy shift impacting Indian markets"

        return {
            "sentiment": overall,
            "score": round(avg, 4),
            "headlines": analyzed[:6],
            "market_impact": impact,
        }

    def get_usa_market_data(self) -> dict:
        """
        Get US market indices data (S&P 500, NASDAQ, Dow Jones) for context.

        Returns:
            Dictionary with US market performance
        """
        try:
            import yfinance as yf

            indices = {
                "S&P 500": "^GSPC",
                "NASDAQ": "^IXIC",
                "Dow Jones": "^DJI",
                "VIX": "^VIX",
            }

            result = {}
            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    if len(hist) >= 2:
                        current = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2]
                        change_pct = ((current - prev) / prev) * 100
                        result[name] = {
                            "value": round(current, 2),
                            "change_pct": round(change_pct, 2),
                            "direction": "Up" if change_pct > 0 else "Down",
                        }
                except Exception:
                    result[name] = {"value": 0, "change_pct": 0, "direction": "Unknown"}

            # Determine overall US market mood
            sp500_change = result.get("S&P 500", {}).get("change_pct", 0)
            if sp500_change > 0.5:
                us_mood = "Bullish"
            elif sp500_change < -0.5:
                us_mood = "Bearish"
            else:
                us_mood = "Flat"

            vix_val = result.get("VIX", {}).get("value", 0)
            fear_level = "High Fear" if vix_val > 25 else "Moderate" if vix_val > 18 else "Low Fear (Greed)"

            return {
                "indices": result,
                "us_market_mood": us_mood,
                "fear_index": fear_level,
                "vix_value": vix_val,
                "impact_on_india": self._assess_india_impact(sp500_change, vix_val),
            }
        except Exception as e:
            return {"error": str(e), "indices": {}, "us_market_mood": "Unknown"}

    def get_complete_usa_analysis(self) -> dict:
        """
        Get complete USA analysis combining news, president updates, and market data.

        Returns:
            Comprehensive USA analysis dictionary
        """
        print("    Fetching USA news...")
        news = self.get_usa_news()

        print("    Fetching US President news...")
        president = self.get_president_news()

        print("    Fetching US market data...")
        markets = self.get_usa_market_data()

        # Combined impact score
        news_score = news["overall_score"]
        market_change = markets.get("indices", {}).get("S&P 500", {}).get("change_pct", 0) / 100

        combined_score = (news_score * 0.6) + (market_change * 0.4)

        if combined_score > 0.1:
            combined_impact = "Positive for Indian Markets"
            options_bias = "CE (Bullish)"
        elif combined_score < -0.1:
            combined_impact = "Negative for Indian Markets"
            options_bias = "PE (Bearish)"
        else:
            combined_impact = "Neutral"
            options_bias = "Neutral — wait for clarity"

        return {
            "timestamp": datetime.now().isoformat(),
            "usa_news": news,
            "president_news": president,
            "us_markets": markets,
            "combined_impact": combined_impact,
            "combined_score": round(combined_score, 4),
            "options_bias": options_bias,
            "recommendation": self._generate_recommendation(combined_score, markets),
        }

    def _fetch_news(self, query: str) -> list:
        """
        Fetch news headlines from Google News RSS.

        Args:
            query: Search query string

        Returns:
            List of headline strings
        """
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.find_all("item")

            headlines = []
            for item in items[:15]:
                title = item.find("title")
                if title:
                    text = title.get_text()
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        headlines.append(text)

            return headlines

        except Exception as e:
            print(f"Warning: Could not fetch USA news for '{query}': {e}")
            return []

    def _assess_india_impact(self, sp500_change: float, vix: float) -> str:
        """Assess how US market conditions impact Indian markets."""
        if sp500_change > 1.0 and vix < 20:
            return "Strong positive — expect gap-up opening in Indian markets"
        elif sp500_change > 0.5:
            return "Mildly positive — Indian markets likely to open flat to positive"
        elif sp500_change < -1.0 or vix > 30:
            return "Strong negative — expect gap-down opening in Indian markets"
        elif sp500_change < -0.5:
            return "Mildly negative — Indian markets may face selling pressure"
        else:
            return "Neutral — Indian markets to follow domestic cues"

    def _generate_recommendation(self, combined_score: float, markets: dict) -> str:
        """Generate actionable recommendation based on USA analysis."""
        vix = markets.get("vix_value", 15)

        if combined_score > 0.15 and vix < 20:
            return (
                "US sentiment is positive with low fear. "
                "Consider NIFTY/BANKNIFTY CE options. "
                "IT stocks (TCS, INFY, WIPRO) may benefit from strong US tech sentiment."
            )
        elif combined_score > 0.05:
            return (
                "US sentiment is mildly positive. "
                "Market may open flat to positive. "
                "Wait for first 15 minutes before taking positions."
            )
        elif combined_score < -0.15 or vix > 25:
            return (
                "US sentiment is negative / high fear. "
                "Consider NIFTY/BANKNIFTY PE options or hedge existing positions. "
                "Avoid aggressive long positions in early trade."
            )
        elif combined_score < -0.05:
            return (
                "US sentiment is mildly negative. "
                "Be cautious with new longs. "
                "Export-heavy stocks may face pressure if USD strengthens."
            )
        else:
            return (
                "US cues are neutral. "
                "Indian markets will likely follow domestic triggers. "
                "Focus on stock-specific setups rather than index trades."
            )
