# services/stock_screener_service.py
class StockScreenerService:
    def __init__(self, screener, db_connection):
        self.screener = screener
        self.db_connection = db_connection

    def process_screener(self, user_id, weights):
        cursor = self.db_connection.cursor()

        # Save weights to database
        weight_id = self._save_weights(cursor, user_id, weights)

        # Set indicators
        self.screener.indicators = {k: v / 100 for k, v in weights.items() if k != 'stock_universe'}

        # Fetch and rank stocks
        ranked_stocks = self._rank_stocks(weights['stock_universe'])

        # Save results and fetch for display
        results = self._save_results(cursor, user_id, weight_id, ranked_stocks)

        self.db_connection.commit()
        return results

    def _save_weights(self, cursor, user_id, weights):
        cursor.execute(
            '''INSERT INTO indicator_weights (user_id, relative_volume, news_event, price_movement, 
            historical_volatility, available_shares, stock_universe) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                user_id,
                weights['relative_volume'],
                weights['news_event'],
                weights['price_movement'],
                weights['historical_volatility'],
                weights['available_shares'],
                weights['stock_universe'],
            )
        )
        return cursor.lastrowid

    def _rank_stocks(self, stock_universe):
        tickers = self.screener.fetch_tickers_from_file(
            'stock_data/sp500_all_tickers.txt' if stock_universe == 'sp500' else 'stock_data/all_tickers.txt'
        )
        stock_data = self.screener.fetch_stock_data(tickers)
        return self.screener.rank_stocks(stock_data)

    def _save_results(self, cursor, user_id, weight_id, ranked_stocks):
        results = []
        for ticker, score in ranked_stocks[:10]:
            market_sentiment = self.screener.get_market_sentiment(ticker)
            cursor.execute(
                '''INSERT INTO indicator_results (user_id, weight_id, ticker, score, market_sentiment) 
                VALUES (?, ?, ?, ?, ?)''',
                (user_id, weight_id, ticker, score, market_sentiment),
            )
            results.append([ticker, score, market_sentiment])
        return results
