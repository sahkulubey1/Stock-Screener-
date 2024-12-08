import base64
import yfinance as yf
from datetime import datetime
from modules.technical_analysis import fetch_and_plot_stock_charts, fetch_technical_indicators

class StockDetailService:
    def __init__(self, ticker):
        self.ticker = ticker
        self.stock_info = yf.Ticker(ticker)
        self.historical_data = None
        self.technical_indicators = None
        self.stock_details = None

    def fetch_charts(self):
        try:
            # Fetch chart images
            price_chart_image, rsi_chart_image, macd_chart_image, fibonacci_chart_image = fetch_and_plot_stock_charts(self.ticker)
            # Encode charts to base64
            return {
                "price_chart": base64.b64encode(price_chart_image.getvalue()).decode('utf-8'),
                "rsi_chart": base64.b64encode(rsi_chart_image.getvalue()).decode('utf-8'),
                "macd_chart": base64.b64encode(macd_chart_image.getvalue()).decode('utf-8'),
                "fibonacci_chart": base64.b64encode(fibonacci_chart_image.getvalue()).decode('utf-8')
            }
        except Exception as e:
            print(f"Error fetching charts for {self.ticker}: {e}")
            return {}

    def fetch_historical_data(self):
        try:
            today = datetime.now().weekday()
            period = '5d' if today >= 5 else '1d'
            self.historical_data = self.stock_info.history(period=period)

            if self.historical_data.empty:
                return {"current_price": "N/A", "previous_close": "N/A", "change_percent": "N/A"}

            current_price = self.historical_data['Close'].iloc[-1]
            previous_close = self.historical_data['Close'].iloc[-2] if len(self.historical_data) >= 2 else "N/A"
            change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close != "N/A" else "N/A"
            return {"current_price": current_price, "previous_close": previous_close, "change_percent": change_percent}

        except Exception as e:
            print(f"Error fetching historical data for {self.ticker}: {e}")
            return {"current_price": "N/A", "previous_close": "N/A", "change_percent": "N/A"}

    def fetch_stock_details(self):
        try:
            self.technical_indicators, self.stock_details = fetch_technical_indicators(self.ticker)
            return {
                "full_name": self.stock_details.get('full_name', "N/A"),
                "industry": self.stock_details.get('industry', "N/A"),
                "sector": self.stock_details.get('sector', "N/A")
            }
        except Exception as e:
            print(f"Error fetching stock details for {self.ticker}: {e}")
            return {}

    def fetch_additional_metrics(self):
        try:
            return {
                "market_cap": self.stock_info.info.get('marketCap', 'N/A'),
                "pe_ratio": self.stock_info.info.get('trailingPE', 'N/A'),
                "dividend_yield": float(self.stock_info.info.get('dividendYield', 0.0) or 0.0),
                "volume": self.historical_data['Volume'].iloc[-1] if self.historical_data is not None and not self.historical_data.empty else "N/A",
                "fifty_two_week_high": self.stock_info.info.get('fiftyTwoWeekHigh', 'N/A'),
                "fifty_two_week_low": self.stock_info.info.get('fiftyTwoWeekLow', 'N/A'),
                "beta": self.stock_info.info.get('beta', 'N/A'),
                "analyst_rating": self.stock_info.info.get('recommendationKey', 'N/A')
            }
        except Exception as e:
            print(f"Error fetching additional metrics for {self.ticker}: {e}")
            return {}

    def fetch_ichimoku_values(self):
        if self.technical_indicators is not None and not self.technical_indicators.empty:
            ichimoku_values = self.technical_indicators.iloc[-1]
            return {
                "ichimoku_tenkan": ichimoku_values.get('tenkan_sen', "N/A"),
                "ichimoku_kijun": ichimoku_values.get('kijun_sen', "N/A"),
                "ichimoku_span_a": ichimoku_values.get('senkou_span_a', "N/A"),
                "ichimoku_span_b": ichimoku_values.get('senkou_span_b', "N/A"),
                "ichimoku_chikou": ichimoku_values.get('chikou_span', "N/A")
            }
        return {}