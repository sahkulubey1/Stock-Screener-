from flask import render_template, request, redirect, url_for, session, flash, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class AuthController:
    def __init__(self, otp_verifier):
        self.otp_verifier = otp_verifier

    def get_db_connection(self):
        if current_app.config['TESTING']:
            # Use an in-memory database for testing
            conn = sqlite3.connect(':memory:')
        else:
            # Use the actual database file in production
            conn = sqlite3.connect('database/database.db')

        conn.row_factory = sqlite3.Row
        return conn

    def require_login(self):
        allowed_routes = ['login', 'register', 'forgot_password_method', 'validate_reset_otp_method',
                          'reset_password_method']
        if 'logged_in' not in session and request.endpoint not in allowed_routes:
            return redirect(url_for('login'))

    def inject_user(self):
        if 'user_id' in session:
            conn = self.get_db_connection()

            # Create user table if it doesn't exist (for testing purposes)
            conn.execute('''CREATE TABLE IF NOT EXISTS user (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL,
                                email TEXT NOT NULL,
                                password TEXT NOT NULL
                            )''')

            # Retrieve user from the database
            user = conn.execute('SELECT * FROM user WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()

            return {'user': dict(user) if user else None}

        return {'user': None}

    def otp_verification(self):
        if request.method == 'POST':
            input_otp = request.form['otp']
            user_id = session.get('user_id')  # Retrieve the stored user_id from session

            if user_id and self.otp_verifier.validate_otp(user_id, int(input_otp)):
                # OTP is correct, mark user as verified
                conn = self.get_db_connection()
                conn.execute('UPDATE user SET is_verified = 1 WHERE id = ?', (user_id,))
                conn.commit()
                conn.close()

                session['logged_in'] = True  # Mark the user as logged in after OTP verification
                flash("OTP verified! You are now logged in.", 'success')
                return redirect(url_for('welcome'))
            else:
                flash("Invalid OTP. Please try again.", 'danger')

        return render_template('validate_otp.html')

    def register_method(self):
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            password_confirmation = request.form['password_confirmation']

            if len(username) < 8:
                flash('Username must be at least 8 characters long.', 'danger')
                return render_template('register.html')

            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
                return render_template('register.html')

            if password != password_confirmation:
                flash('Passwords do not match. Please try again.', 'danger')
                return render_template('register.html')

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            conn = self.get_db_connection()
            try:
                conn.execute('INSERT INTO user (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_password))
                conn.commit()
                flash('You have successfully registered! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already exists. Please try another.', 'danger')
            finally:
                conn.close()

        return render_template('register.html')

    def login_method(self):
        """Handles user login with OTP verification if required."""
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            try:
                # Database connection
                conn = self.get_db_connection()
                user = conn.execute('SELECT * FROM user WHERE email = ?', (email,)).fetchone()
                conn.close()

                if user and check_password_hash(user['password'], password):
                    if not user['is_verified']:
                        # Generate and send OTP
                        otp = self.otp_verifier.generate_otp(user['id'])
                        self.otp_verifier.send_otp_email(email, otp, subject="Your OTP Code")

                        # Set session variables
                        session['user_id'] = user['id']
                        session['logged_in'] = False

                        flash('OTP sent! Please check your email.', 'info')
                        return redirect(url_for('otp_verification'))
                    else:
                        # User is verified, log in
                        session['user_id'] = user['id']
                        session['logged_in'] = True
                        session['username'] = user['username']

                        flash('Login successful!', 'success')
                        return redirect(url_for('welcome'))

                # Invalid credentials
                flash('Invalid email or password.', 'danger')

            except sqlite3.OperationalError as e:
                # Database-related issues (e.g., the query fails)
                print(f"Database error: {e}")  # Log for debugging
                flash('Invalid credentials or a database issue. Please try again later.', 'danger')
            except Exception as e:
                # Catch unexpected errors
                print(f"Unexpected error: {e}")  # Log for debugging
                flash('An unexpected error occurred. Please try again.', 'danger')

        # Render login page on GET request or after an error
        return render_template('login.html')

    def welcome(self):
        username = session.get('username')
        return render_template('welcome.html', username=username)

    def forgot_password(self, email):
        try:
            # Check the email address in the database
            conn = self.get_db_connection()

            # Create user table if it doesn't exist (for testing purposes)
            conn.execute('''CREATE TABLE IF NOT EXISTS user (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL,
                                email TEXT NOT NULL,
                                password TEXT NOT NULL
                            )''')

            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user WHERE email = ?', (email,))
            user = cursor.fetchone()
            conn.close()

            if user:
                # Send OTP
                otp = self.otp_verifier.send_password_reset_email(email, user['id'])
                print(f"Debugging: OTP sent for user_id={user['id']}: {otp}")
                flash('OTP sent to your email.', 'info')
                return {'success': True, 'user_id': user['id']}
            else:
                flash('Email not found. Please try again.', 'danger')
                return {'success': False}
        except sqlite3.OperationalError as e:
            # Handle case where the user table is missing or there is a database-related issue
            print(f"Database error: {e}")  # Log for debugging
            flash('There was an error with the database. Please try again later.', 'danger')
            return {'success': False}

    def validate_reset_otp(self, user_id, input_otp):
        # OTP Verification
        is_valid, message = self.otp_verifier.verify_password_reset_otp(int(user_id), int(input_otp))
        if is_valid:
            flash(message, 'success')
            return {'success': True}
        else:
            flash(message, 'danger')
            return {'success': False, 'error_message': message}

    def logout_method(self):
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))
