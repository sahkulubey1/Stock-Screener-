from flask import render_template, request, redirect, url_for, session, flash, get_flashed_messages, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class ProfileController:
    def __init__(self):
        pass

    def get_db_connection(self):
        if current_app.config['TESTING']:
            # Use an in-memory database for testing
            conn = sqlite3.connect(':memory:')
        else:
            # Use the actual database file in production
            conn = sqlite3.connect('database/database.db')

        conn.row_factory = sqlite3.Row
        return conn

    def profile(self, user_id):
        # Retrieve user from the database
        conn = self.get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        conn.close()

        # Filter messages
        all_messages = get_flashed_messages(with_categories=True)
        messages = [
            msg for msg in all_messages
            if not any(word in msg[1].lower() for word in ['login', 'otp', 'register'])
        ]

        return {'user': dict(user) if user else None, 'messages': messages}

    def update_user(self, user_id, username, email):
        """Update the user's profile (username, email)."""

        # Ensure the 'user' table exists (this is a safeguard)
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        conn.commit()

        # Now perform the update operation
        cursor.execute(
            'UPDATE user SET username = ?, email = ? WHERE id = ?',
            (username, email, user_id)
        )
        conn.commit()
        conn.close()

        # Return a success message
        flash('Profile updated successfully!', 'success')

    def reset_password(self, user_id, new_password, confirm_password):
        """Reset the user's password."""

        # Step 1: Check if the new password matches the confirmation password
        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return False

        # Step 2: Check if the new password is at least 8 characters long
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return False

        try:
            # Step 3: Establish DB connection
            conn = self.get_db_connection()

            # Step 4: Check if the user exists in the database
            user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()

            if user is None:
                flash('User not found!', 'danger')
                return False

            # Step 5: Hash the new password
            hashed_password = generate_password_hash(new_password)

            # Step 6: Update the user's password
            conn.execute(
                'UPDATE user SET password = ? WHERE id = ?',
                (hashed_password, user_id)
            )
            conn.commit()
            conn.close()

            # Step 7: Return success message
            flash('Password updated successfully!', 'success')
            return True

        except sqlite3.Error as e:
            # Handle any SQLite errors
            flash(f'Database error: {str(e)}', 'danger')
            return False
        except Exception as e:
            # Handle any other exceptions
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return False

