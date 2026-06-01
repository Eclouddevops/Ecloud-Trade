"""
Company Fundamentals Module
Fetches company info, financials, balance sheet, and cash flow data.
"""
import yfinance as yf


class CompanyFundamentals:
    """Fetches and analyzes company fundamental data."""

    def get_company_info(self, symbol: str) -> dict:
        """Get company overview information."""
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        return {
            "name": info.get("longName", symbol),
            "symbol": symbol,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "enterprise_value": info.get("enterpriseValue", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "book_value": info.get("bookValue"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "website": info.get("website", ""),
            "description": info.get("longBusinessSummary", "")[:300],
        }

    def get_financials(self, symbol: str) -> dict:
        """Get quarterly and annual financial data."""
        ticker = yf.Ticker(f"{symbol}.NS")
        result = {"quarterly": [], "annual": []}

        # Quarterly
        try:
            q_fin = ticker.quarterly_financials
            if q_fin is not None and not q_fin.empty:
                for col in q_fin.columns[:4]:
                    quarter_data = {
                        "period": col.strftime("%b %Y"),
                        "revenue": self._fmt(q_fin.loc["Total Revenue", col]) if "Total Revenue" in q_fin.index else None,
                        "net_income": self._fmt(q_fin.loc["Net Income", col]) if "Net Income" in q_fin.index else None,
                        "ebit": self._fmt(q_fin.loc["EBIT", col]) if "EBIT" in q_fin.index else None,
                    }
                    result["quarterly"].append(quarter_data)
        except Exception:
            pass

        # Annual
        try:
            a_fin = ticker.financials
            if a_fin is not None and not a_fin.empty:
                for col in a_fin.columns[:5]:
                    annual_data = {
                        "period": col.strftime("%Y"),
                        "revenue": self._fmt(a_fin.loc["Total Revenue", col]) if "Total Revenue" in a_fin.index else None,
                        "net_income": self._fmt(a_fin.loc["Net Income", col]) if "Net Income" in a_fin.index else None,
                        "ebit": self._fmt(a_fin.loc["EBIT", col]) if "EBIT" in a_fin.index else None,
                    }
                    result["annual"].append(annual_data)
        except Exception:
            pass

        return result

    def get_balance_sheet(self, symbol: str) -> dict:
        """Get balance sheet data."""
        ticker = yf.Ticker(f"{symbol}.NS")
        try:
            bs = ticker.balance_sheet
            if bs is None or bs.empty:
                return {}
            latest = bs.iloc[:, 0]
            return {
                "total_assets": self._fmt(latest.get("Total Assets")),
                "total_liabilities": self._fmt(latest.get("Total Liabilities Net Minority Interest")),
                "total_debt": self._fmt(latest.get("Total Debt")),
                "cash": self._fmt(latest.get("Cash And Cash Equivalents")),
                "stockholders_equity": self._fmt(latest.get("Stockholders Equity")),
            }
        except Exception:
            return {}

    def get_cashflow(self, symbol: str) -> dict:
        """Get cash flow statement."""
        ticker = yf.Ticker(f"{symbol}.NS")
        try:
            cf = ticker.cashflow
            if cf is None or cf.empty:
                return {}
            latest = cf.iloc[:, 0]
            return {
                "operating_cf": self._fmt(latest.get("Operating Cash Flow")),
                "investing_cf": self._fmt(latest.get("Investing Cash Flow")),
                "financing_cf": self._fmt(latest.get("Financing Cash Flow")),
                "free_cf": self._fmt(latest.get("Free Cash Flow")),
            }
        except Exception:
            return {}

    def _fmt(self, val):
        """Format large numbers to crores."""
        if val is None or (hasattr(val, '__class__') and val.__class__.__name__ == 'NaTType'):
            return None
        try:
            v = float(val)
            if abs(v) >= 1e7:
                return round(v / 1e7, 2)  # In crores
            return round(v, 2)
        except (ValueError, TypeError):
            return None
