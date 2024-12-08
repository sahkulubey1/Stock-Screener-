import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail
from modules.screener import StockScreener
from services.stock_screener_service import StockScreenerService
from modules.technical_analysis import fetch_and_plot_stock_charts
import base64
from modules.technical_analysis import fetch_technical_indicators
import yfinance as yf
from datetime import datetime
import sqlite3
import os
from werkzeug.security import generate_password_hash
from controllers.auth_controller import AuthController
from controllers.history_controller import HistoryController
from controllers.profile_controller import ProfileController
from modules.otp_verification import OTPVerifier
from dotenv import load_dotenv

load_dotenv()
screener_to_retrieve_data = StockScreener(api_key=os.getenv("API_KEY"))
app = Flask(__name__)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Using Gmail's SMTP server
app.config['MAIL_PORT'] = 587  # Use port 587 for TLS
app.config['MAIL_USE_TLS'] = True  # Enable TLS
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")  # Your email address
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")  # Your email password (or app password if using Gmail)
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("EMAIL_USER")  # The default sender email
app.secret_key = secrets.token_hex(16)
mail = Mail(app)
otp_verifier = OTPVerifier(app)

auth_controller = AuthController(otp_verifier)
history_controller = HistoryController()
profile_controller = ProfileController()

# Before request to check if user is logged in for all routes except login and register
@app.before_request
def require_login():
    return auth_controller.require_login()

@app.route('/register', methods=['GET', 'POST'])
def register():
    return auth_controller.register_method()

@app.route('/login', methods=['GET', 'POST'])
def login():
    return auth_controller.login_method()

# Database Connection
def get_db_connection():
    # Define the absolute path to the database file
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'database.db')

    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Try to connect to the database
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Use Row factory to access columns by name
        return conn
    except sqlite3.OperationalError as e:
        print(f"Error connecting to database: {e}")
        raise  # Reraise the exception so the caller is aware of the issue

@app.context_processor
def inject_user():
    return auth_controller.inject_user()

# OTP Verification Route
@app.route('/otp_verification', methods=['GET', 'POST'])
def otp_verification():
    return auth_controller.otp_verification()

@app.route('/welcome')
def welcome():
    return auth_controller.welcome()

@app.route('/logout')
def logout():
    return auth_controller.logout_method()


# Stock Screener Route (Accessible after login)
@app.route('/stock_screener')
def stock_screener():
    # Debugging session data to check if the user is logged in
    print("Session Data: ", session)

    if 'logged_in' not in session or not session['logged_in']:
        flash("Please log in first.", 'danger')
        return redirect(url_for('login'))  # Redirect to login if not logged in

    return render_template('stock_screener.html')


@app.route('/history_filter', methods=['GET'])
def history_filter():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return "Unauthorized", 403

    # Get start_date and end_date from the query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Call the HistoryController's method
    data = history_controller.history_filter(session['user_id'], start_date, end_date)
    return render_template('history.html', user=data['user'], weights_with_results=data['weights_with_results'])

# Profile Page (Only accessible when logged in)
@app.route('/history/')
def history():
    if 'user_id' not in session:
        return "Unauthorized", 403  # Prevent access if not logged in

    # Call the HistoryController's method
    data = history_controller.history(session['user_id'])
    return render_template('history.html', user=data['user'], weights_with_results=data['weights_with_results'])

# Profile Route
@app.route('/profile/')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  #if user is not in the session, direct to the login

    #get the user data and messages from ProfileController
    data = profile_controller.profile(session['user_id'])
    return render_template('profile.html', user=data['user'], messages=data['messages'])


# Update Profile Route
@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Ensure user is logged in

    # Retrieve the user data from the session
    user_id = session['user_id']
    username = request.form['username']
    email = request.form['email']

    # Update the user in the database
    conn = get_db_connection()
    conn.execute('UPDATE user SET username = ?, email = ? WHERE id = ?', (username, email, user_id))
    conn.commit()
    conn.close()

    # After the update, redirect to the profile page
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))  # Redirect to profile page to show updated data


# Reset Password Route
@app.route('/profile/reset_password', methods=['POST'])
def reset_password():
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if not profile_controller.reset_password(session['user_id'], new_password, confirm_password):
        return redirect(url_for('profile'))

    return redirect(url_for('profile'))



# Forgot Password Route
@app.route('/forgot_password_method', methods=['GET', 'POST'])
def forgot_password_method():
    if request.method == 'POST':
        email = request.form['email']

        # Call the method in AuthController
        result = auth_controller.forgot_password(email)

        if result['success']:
            return redirect(url_for('validate_reset_otp_method', user_id=result['user_id']))

    return render_template('forgot_password.html')

@app.route('/validate_reset_otp_method', methods=['GET', 'POST'])
def validate_reset_otp_method():
    user_id = request.args.get('user_id')
    print("Debugging in validate_reset_otp_method: user_id =", user_id)

    error_message = None

    if request.method == 'POST':
        input_otp = request.form['otp']
        print("Debugging: input_otp =", input_otp)

        result = auth_controller.validate_reset_otp(user_id, input_otp)

        if result['success']:
            return redirect(url_for('reset_password_method', user_id=user_id))
        else:
            error_message = result['error_message']

    return render_template('validate_reset_otp.html', user_id=user_id, error_message=error_message)


@app.route('/reset_password_method/<user_id>', methods=['GET', 'POST'])
def reset_password_method(user_id):
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['password_confirmation']

        # Check if passwords match
        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('reset_password.html', user_id=user_id)

        # Check if password length is valid (at least 8 characters)
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('reset_password.html', user_id=user_id)

        # Hash the new password
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

        try:
            # Get the database connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # Update password in the database
            cursor.execute('UPDATE user SET password = ? WHERE id = ?', (hashed_password, user_id))
            conn.commit()
            conn.close()

            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'danger')
            return render_template('reset_password.html', user_id=user_id)
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return render_template('reset_password.html', user_id=user_id)

    return render_template('reset_password.html', user_id=user_id)  # Include user_id to identify the user


@app.route('/')
def stock_search():
    return render_template('stock_search.html')

@app.route('/learn_more')
def learn_more():
    return render_template('learn_more.html')

@app.route('/stock-screener')
def index():
    return render_template('stock_screener.html')


@app.route('/run_screener', methods=['POST'])
def run_screener():
    try:
        user_id = session.get('user_id')

        # Retrieve weights from the form and call the service
        weights = {key: float(request.form.get(key, 0)) for key in
                   ['relative_volume', 'news_event', 'price_movement', 'historical_volatility', 'available_shares']}
        weights['stock_universe'] = request.form['stock_universe']

        # Delegate business logic to the service
        with get_db_connection() as db_connection:
            screener_service = StockScreenerService(screener_to_retrieve_data, db_connection)
            results = screener_service.process_screener(user_id, weights)

        return render_template('stock_screener_results.html', stocks=results)
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/stock/<ticker>')
def stock_details(ticker):
    # Fetch the charts images in memory
    global historical_data
    price_chart_image, rsi_chart_image, macd_chart_image, fibonacci_chart_image = fetch_and_plot_stock_charts(ticker)

    # Encode the images to base64
    price_chart_base64 = base64.b64encode(price_chart_image.getvalue()).decode('utf-8')
    rsi_chart_base64 = base64.b64encode(rsi_chart_image.getvalue()).decode('utf-8')
    macd_chart_base64 = base64.b64encode(macd_chart_image.getvalue()).decode('utf-8')
    fibonacci_chart_base64 = base64.b64encode(fibonacci_chart_image.getvalue()).decode('utf-8')

    technical_indicators, stock_details = fetch_technical_indicators(ticker)

    # Fetch additional stock metrics using yfinance
    stock_info = yf.Ticker(ticker)

    today = datetime.now().weekday()
    period = '5d' if today >= 5 else '1d'

    # Fetch historical data
    try:

        historical_data = stock_info.history(period=period)
        if historical_data.empty:
            current_price = "N/A"
            previous_close = "N/A"
            change_percent = "N/A"
        else:
            current_price = historical_data['Close'].iloc[-1]

            # Calculate previous close and change percent safely
            if len(historical_data) >= 2:
                previous_close = historical_data['Close'].iloc[-2]
                change_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                previous_close = "N/A"
                change_percent = "N/A"
    except Exception as e:
        print(f"Error fetching historical data for {ticker}: {e}")
        current_price = "N/A"
        previous_close = "N/A"
        change_percent = "N/A"

    market_cap = stock_info.info.get('marketCap', 'N/A')
    pe_ratio = stock_info.info.get('trailingPE', 'N/A')
    dividend_yield = stock_info.info.get('dividendYield', 'N/A')
    volume = historical_data['Volume'].iloc[-1] if not historical_data.empty else "N/A"

    full_name = stock_details.get('full_name', "N/A")
    industry = stock_details.get('industry', "N/A")
    sector = stock_details.get('sector', "N/A")

    if technical_indicators is not None and not technical_indicators.empty:
        ichimoku_values = technical_indicators.iloc[-1]
        ichimoku_tenkan = ichimoku_values.get('tenkan_sen', "N/A")
        ichimoku_kijun = ichimoku_values.get('kijun_sen', "N/A")
        ichimoku_span_a = ichimoku_values.get('senkou_span_a', "N/A")
        ichimoku_span_b = ichimoku_values.get('senkou_span_b', "N/A")
        ichimoku_chikou = ichimoku_values.get('chikou_span', "N/A")
    else:
        ichimoku_tenkan = ichimoku_kijun = ichimoku_span_a = ichimoku_span_b = ichimoku_chikou = "N/A"

    daily_return = (current_price - technical_indicators['SMA'].iloc[-1]) / technical_indicators['SMA'].iloc[
        -1] * 100 if 'SMA' in technical_indicators.columns else "N/A"
    fifty_two_week_high = stock_info.info.get('fiftyTwoWeekHigh', 'N/A')
    fifty_two_week_low = stock_info.info.get('fiftyTwoWeekLow', 'N/A')
    beta = stock_info.info.get('beta', 'N/A')
    analyst_rating = stock_info.info.get('recommendationKey', 'N/A')

    if dividend_yield in ["N/A", ""]:
        dividend_yield = 0.0
    else:
        try:
            dividend_yield = float(dividend_yield)
        except ValueError:
            dividend_yield = 0.0

    return render_template(
        'stock_details.html',
        ticker=ticker,
        price_chart_image=price_chart_base64,
        rsi_chart_image=rsi_chart_base64,
        macd_chart_image=macd_chart_base64,
        fibonacci_chart_image=fibonacci_chart_base64,
        technical_indicators=technical_indicators,
        current_price=current_price,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        dividend_yield=dividend_yield,
        volume=volume,
        change_percent=change_percent,
        ichimoku_tenkan=ichimoku_tenkan,
        ichimoku_kijun=ichimoku_kijun,
        ichimoku_span_a=ichimoku_span_a,
        ichimoku_span_b=ichimoku_span_b,
        ichimoku_chikou=ichimoku_chikou,
        daily_return=daily_return,
        fifty_two_week_high=fifty_two_week_high,
        fifty_two_week_low=fifty_two_week_low,
        beta=beta,
        analyst_rating=analyst_rating,
        full_name=full_name,
        industry=industry,
        sector=sector
    )


if __name__ == '__main__':
    app.run(debug=True)