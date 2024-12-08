import yfinance as yf
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor


class StockScreener:
    MAX_ARTICLES = 10  # Maximum number of articles for sentiment analysis

    def __init__(self, api_key=None, indicators=None):
        self.indicators = indicators or {
            'relative_volume': 0,
            'price_movement': 0,
            'historical_volatility': 0,
            'available_shares': 0,
        }
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.api_key = api_key

        # Debugging line to check if the API key is set
        if self.api_key:
            print(f"API key set: {self.api_key}")
        else:
            print("API key is not set!")

    def fetch_tickers_from_file(self, file_path):
        """Fetch the list of stock tickers"""
        try:
            with open(file_path, 'r') as file:
                tickers = [line.strip() for line in file if line.strip()]
            print(f"Loaded {len(tickers)} tickers from {file_path}.")  # Debugging output
            return tickers
        except FileNotFoundError:
            print(f"File {file_path} not found. Please check the path.")
            return []

    def calculate_historical_volatility(self, prices):
        """Calculate the historical volatility of a stock using the last 5 days of prices."""
        if len(prices) < 2:
            return 0  # Not enough data to calculate volatility

        # Ensure prices do not contain NaN or invalid values
        prices = [price for price in prices if price is not None and not np.isnan(price)]
        if len(prices) < 2:
            return 0

        returns = np.diff(prices) / prices[:-1]

        # Calculate the standard deviation of daily returns
        volatility = np.std(returns)

        # Annualize the volatility for comparison, if needed (optional)
        annualized_volatility = volatility * np.sqrt(252) * 100

        return annualized_volatility if not np.isnan(annualized_volatility) else 0

    def calculate_indicators(self, ticker):
        """Calculate indicators for a single stock."""
        stock_info = yf.Ticker(ticker).info
        historical_data = yf.Ticker(ticker).history(period="5d")  # Fetch 5 days of data

        total_volume = historical_data['Volume'].sum()
        if total_volume < 5_000_000:  # 5 million
            print(f"Skipping {ticker} due to low volume: {total_volume}")
            return None

        market_cap = stock_info.get('marketCap', 0)
        if market_cap < 500_000_000:  # 500 million
            print(f"Skipping {ticker} due to low market cap: {market_cap}")
            return None

        if historical_data.empty:
            print(f"No historical data for {ticker}.")
            return None

        current_price = stock_info.get('currentPrice', 0)
        yearly_avg_volume = historical_data['Volume'].mean()
        historical_prices = historical_data['Close'].tolist()

        # Calculate historical volatility
        volatility = self.calculate_historical_volatility(historical_prices)

        # Calculate relative volume
        relative_volume = (historical_data['Volume'].iloc[-1] / yearly_avg_volume) if yearly_avg_volume else 0

        # Improved price movement calculation
        max_price = historical_data['Close'].max()
        min_price = historical_data['Close'].min()
        price_movement = ((max_price - min_price) / min_price) * 100 if min_price else 0

        # Debugging output
        print(f"{ticker}: Current Price={current_price}, Relative Volume={relative_volume}, "
              f"Price Movement={price_movement}, Historical Volatility={volatility}, "
              f"Available Shares={stock_info.get('sharesOutstanding', 0) / 1e6}")

        return {
            'name': ticker,
            'relative_volume': relative_volume,
            'price_movement': price_movement,
            'historical_volatility': volatility,
            'available_shares': stock_info.get('sharesOutstanding', 0) / 1e6
        }

    def fetch_stock_data(self, tickers):
        """Fetch stock data for provided tickers using multithreading."""
        stock_data = []

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.calculate_indicators, ticker): ticker for ticker in tickers[:20]}
            for future in futures:
                ticker = futures[future]
                try:
                    result = future.result()
                    if result:
                        print(f"Fetched data for {ticker}: {result}")  # Debugging output
                        stock_data.append(result)
                except Exception as e:
                    print(f"Error processing ticker {ticker}: {e}")

        print(f"Stock data fetched: {stock_data}")  # Print the entire list of stock data
        return stock_data

    def analyze_sentiment(self, subject):
        """Analyze the sentiment of the given subject and convert the score to percentage."""
        if subject is None or subject.strip() == "":
            print("Received empty subject for sentiment analysis.")  # Debugging output
            return 50  # Neutral sentiment, represented as 50%

        sentiment = self.sentiment_analyzer.polarity_scores(subject)
        # Convert the compound score to a percentage (0 to 100)
        compound_score = sentiment['compound']
        sentiment_percentage = (compound_score + 1) * 50

        return sentiment_percentage

    def get_market_sentiment(self, ticker, max_articles=MAX_ARTICLES):
        """Fetch recent news articles for the stock and analyze sentiment."""

        if not self.api_key:
            print("API key is not set. Please check your initialization.")  # Debugging output
            return 50  # Neutral sentiment score (50%) if API key is not set

        # Define the dates for yesterday and today
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Search news articles related to the ticker
        url = f"https://newsapi.org/v2/everything?q={ticker}&from={yesterday}&to={today}&sortBy=popularity&apiKey={self.api_key}"

        try:
            response = requests.get(url, timeout=10)  # Set a timeout
            response.raise_for_status()  # Raise an error for bad responses
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news for {ticker}: {e}")
            return 50  # Return neutral sentiment score if the request fails


        if response.status_code != 200:
            print(f"Error fetching news for {ticker}: {response.status_code}")  # Debugging output
            return 50  # Return neutral sentiment score (50%) if API call fails

        articles = response.json().get('articles', [])
        if not articles:
            print(f"No articles found for {ticker}.")  # Debugging output
            return 50  # Return neutral sentiment score (50%) if no articles found

        # Limit to the first MAX_ARTICLES articles for sentiment analysis
        sentiments = [self.analyze_sentiment(article['content']) for article in articles[:max_articles]]

        # Calculate average sentiment as a percentage
        average_sentiment = np.mean(sentiments) if sentiments else 50

        print(f"Average sentiment for {ticker}: {average_sentiment}%")  # Debugging output
        return average_sentiment

    def rank_stocks(self, stock_data):
        """Rank stocks based on the screener criteria."""
        if not isinstance(stock_data, list):
            print(f"Error: Expected list, got {type(stock_data)}")  # Debugging output
            return []

        ranked_stocks = []

        for stock in stock_data:
            if isinstance(stock, dict):  # Ensure stock is a dictionary
                score = (
                    self.indicators['relative_volume'] * stock['relative_volume'] +
                    self.indicators['price_movement'] * stock['price_movement'] +
                    self.indicators['historical_volatility'] * stock['historical_volatility'] +
                    self.indicators['available_shares'] * (1 / stock['available_shares']) if stock[
                        'available_shares'] else 0  # Inverse relationship
                )
                ranked_stocks.append((stock['name'], score))
            else:
                print(f"Unexpected stock data format: {stock}")  # Debugging output

        # Normalizing scores and printing debug info
        print("Raw Scores:")
        for stock, score in ranked_stocks:
            print(f"{stock}: Score={score}")

        # Normalize scores using log transformation and min-max scaling
        scores = np.array([ranked_stock[1] for ranked_stock in ranked_stocks])
        log_scores = np.log1p(scores)  # Use log1p to avoid log(0)

        max_score = np.max(log_scores)
        min_score = np.min(log_scores)

        # Min-Max Scaling
        normalized_scores = (
                (log_scores - min_score) / (max_score - min_score) * 100
        ).tolist()

        # Combine normalized scores with stock names
        normalized_scores = list(zip([ranked_stock[0] for ranked_stock in ranked_stocks], normalized_scores))

        # Print normalized scores for debugging
        print("Normalized Scores:")
        for stock, score in normalized_scores:
            print(f"{stock}: Normalized Score={score}")

        # Sort stocks by normalized score in descending order
        normalized_scores.sort(key=lambda x: x[1], reverse=True)
        return normalized_scores
