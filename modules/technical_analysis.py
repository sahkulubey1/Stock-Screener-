import time
import ta
import yfinance as yf
import matplotlib.pyplot as plt
from io import BytesIO


def fetch_stock_details(ticker):
    """Fetch additional stock details such as full name, industry, and sector."""
    stock = yf.Ticker(ticker)
    stock_info = stock.info

    # Extract relevant details
    full_name = stock_info.get('longName', 'N/A')
    industry = stock_info.get('industry', 'N/A')
    sector = stock_info.get('sector', 'N/A')
    market_cap = stock_info.get('marketCap', 'N/A')

    return {
        'full_name': full_name,
        'industry': industry,
        'sector': sector,
        'market_cap': market_cap
    }


def fetch_technical_indicators(ticker):
    """Fetch and calculate technical indicators for a given stock ticker."""
    stock_data = yf.download(ticker, period="1y")
    stock_data = stock_data.dropna()

    # Fetch stock details
    stock_details = fetch_stock_details(ticker)

    # Volume Indicators
    # Squeeze the series to ensure it is 1D
    stock_data['MFI'] = ta.volume.MFIIndicator(stock_data['High'].squeeze(),
                                               stock_data['Low'].squeeze(),
                                               stock_data['Close'].squeeze(),
                                               stock_data['Volume'].squeeze()).money_flow_index()
    stock_data['OBV'] = ta.volume.OnBalanceVolumeIndicator(stock_data['Close'].squeeze(),
                                                           stock_data['Volume'].squeeze()).on_balance_volume()

    # Volatility Indicators
    stock_data['ATR'] = ta.volatility.AverageTrueRange(stock_data['High'].squeeze(),
                                                       stock_data['Low'].squeeze(),
                                                       stock_data['Close'].squeeze()).average_true_range()
    stock_data['BB_High'] = ta.volatility.BollingerBands(stock_data['Close'].squeeze()).bollinger_hband()
    stock_data['BB_Low'] = ta.volatility.BollingerBands(stock_data['Close'].squeeze()).bollinger_lband()

    # Trend Indicators
    stock_data['SMA'] = ta.trend.SMAIndicator(stock_data['Close'].squeeze(), window=20).sma_indicator()
    stock_data['MACD'] = ta.trend.MACD(stock_data['Close'].squeeze()).macd()

    # Momentum Indicators
    stock_data['RSI'] = ta.momentum.RSIIndicator(stock_data['Close'].squeeze()).rsi()

    # Ichimoku Cloud Components
    high_9 = stock_data['High'].rolling(window=9).max()
    low_9 = stock_data['Low'].rolling(window=9).min()
    stock_data['tenkan_sen'] = (high_9 + low_9) / 2

    high_26 = stock_data['High'].rolling(window=26).max()
    low_26 = stock_data['Low'].rolling(window=26).min()
    stock_data['kijun_sen'] = (high_26 + low_26) / 2

    stock_data['senkou_span_a'] = ((stock_data['tenkan_sen'] + stock_data['kijun_sen']) / 2).shift(26)
    stock_data['senkou_span_b'] = (
            (stock_data['High'].rolling(window=52).max() + stock_data['Low'].rolling(window=52).min()) / 2).shift(
        26)  # Leading Span B
    stock_data['chikou_span'] = stock_data['Close'].shift(-26)  # Lagging Span

    return stock_data.tail(10), stock_details



def create_stock_chart(ticker):
    """Create a line chart for the stock's closing price."""
    stock_data = yf.download(ticker, period='1y')
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price')
    plt.title(f'Stock Price for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()

    # Save chart to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return img


def create_rsi_chart(ticker):
    """Create a line chart for the Relative Strength Index (RSI)."""
    stock_data = yf.download(ticker, period='1y')

    # Ensure 'Close' is a 1D Series (squeeze it if necessary)
    close_prices = stock_data['Close'].squeeze()

    # Now compute the RSI using the 1D Series
    rsi = ta.momentum.RSIIndicator(close_prices).rsi()

    plt.figure(figsize=(10, 0.6))
    plt.plot(rsi, label='RSI', color='purple')
    plt.axhline(70, linestyle='--', alpha=0.5, color='red')
    plt.axhline(30, linestyle='--', alpha=0.5, color='green')
    plt.title(f'RSI for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('RSI')
    plt.legend()
    plt.grid()

    # Save chart to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return img


def create_macd_chart(ticker):
    """Create a line chart for the Moving Average Convergence Divergence (MACD)."""
    stock_data = yf.download(ticker, period='1y')

    # Ensure 'Close' is a 1D Series (squeeze it if necessary)
    close_prices = stock_data['Close'].squeeze()

    # Calculate MACD
    macd = ta.trend.MACD(close_prices)

    plt.figure(figsize=(10, 0.6))
    plt.plot(macd.macd(), label='MACD', color='blue')
    plt.plot(macd.macd_signal(), label='Signal Line', color='orange')
    plt.title(f'MACD for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('MACD')
    plt.legend()
    plt.grid()

    # Save chart to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return img


def calculate_fibonacci_levels(stock_data):
    """Calculate Fibonacci levels based on the stock's high and low prices."""
    high = stock_data['Close'].max()
    low = stock_data['Close'].min()
    diff = high - low

    level1 = high - diff * 0.236
    level2 = high - diff * 0.382
    level3 = high - diff * 0.618
    level4 = high - diff * 0.786

    return level1, level2, level3, level4


def create_fibonacci_chart(ticker):
    """Create a chart showing Fibonacci retracement levels."""
    stock_data = yf.download(ticker, period='1y')
    levels = calculate_fibonacci_levels(stock_data)

    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price', color='blue')

    # Ensure each level is a scalar value, not a Series
    for level in levels:
        plt.axhline(y=level.item(), color='orange', linestyle='--', label=f'Fibonacci Level: {level.item():.2f}')

    plt.title(f'Fibonacci Retracement Levels for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()

    # Save chart to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return img


def fetch_and_plot_stock_charts(ticker):
    """Fetch stock data, technical indicators, and plot the stock charts."""
    price_chart = create_stock_chart(ticker)
    rsi_chart = create_rsi_chart(ticker)
    macd_chart = create_macd_chart(ticker)
    fibonacci_chart = create_fibonacci_chart(ticker)

    return price_chart, rsi_chart, macd_chart, fibonacci_chart
