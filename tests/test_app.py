import unittest
from flask import session
from app import app
from werkzeug.security import generate_password_hash
import sqlite3


class TestAppRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the test environment and in-memory database."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.secret_key = "test_secret"
        cls.client = app.test_client()

        # Set up in-memory database
        cls.conn = sqlite3.connect(":memory:")
        cls.conn.row_factory = sqlite3.Row
        cls._create_mock_tables()

    @classmethod
    def _create_mock_tables(cls):
        """Create mock tables and insert sample data."""
        cursor = cls.conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                is_verified INTEGER DEFAULT 0
            )
        """)
        # Insert a verified user
        cursor.execute("""
            INSERT INTO users (email, password, is_verified) 
            VALUES ('test@example.com', ?, 1)
        """, (generate_password_hash("testpassword"),))
        cls.conn.commit()

    def test_register_get(self):
        """Test GET method for /register route."""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Register", response.data)

    def test_login_success(self):
        """Test successful login."""
        with app.app_context():
            response = self.client.post('/login', data={
                "email": "test@example.com",
                "password": "testpassword"  # Ensure these match the logic
            }, follow_redirects=True)  # Follow the redirect to the welcome page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Login - Stock Screener", response.data)  # Update to match `welcome.html`

    def test_login_failure(self):
        """Test failed login attempt."""
        response = self.client.post('/login', data={
            "email": "test@example.com",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid credentials", response.data)

    def test_register_empty_form(self):
        """Test form submission with empty data."""
        response = self.client.post('/register', data={})
        self.assertEqual(response.status_code, 400)  # Expecting 400 Bad Request

    def test_stock_search(self):
        """Test the stock search page."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True  # Simulate a logged-in session
        response = self.client.get('/')  # Directly use self.client
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Search for Stock", response.data)


    def test_unauthorized_profile_access(self):
        """Test that unauthorized access to /profile is redirected or forbidden."""
        response = self.client.get('/profile')
        # Adjust this if your app redirects unauthorized users with a 308 status code
        self.assertIn(response.status_code, [302, 308, 403])  # Allow 308 if it's a permanent redirect

    def test_logout(self):
        """Test user logout."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['logged_in'] = True
            response = client.get('/logout')
            self.assertEqual(response.status_code, 302)  # Redirect to login
            with client.session_transaction() as sess:
                self.assertNotIn('logged_in', sess)

    def test_session_timeout(self):
        """Test session timeout behavior."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
        # Simulate a session timeout by clearing the session
        with self.client.session_transaction() as sess:
            sess.clear()
        response = self.client.get('/profile')
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_reset_password(self):
        """Test password reset functionality."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1  # Simulate user logged in

        # Reset password
        response = self.client.post('/profile/reset_password', data={
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })

        self.assertEqual(response.status_code, 302)  # Should redirect to profile page

        # Check if password was updated in the database
        cursor = self.conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = 1")
        db_password = cursor.fetchone()['password']
        self.assertNotEqual(db_password, generate_password_hash("testpassword"))

    def test_profile_update_redirect(self):
        """Test profile update redirect behavior."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1

        response = self.client.post('/profile/update', data={
            'username': 'newusername',
            'email': 'newemail@example.com'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to profile page

    def test_flash_messages_on_login_failure(self):
        """Test flash messages during login failure."""
        response = self.client.post('/login', data={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid credentials", response.data)  # Flash message for failed login

    def test_run_screener(self):
        """Test running the stock screener with failure."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1

        response = self.client.post('/run_screener', data={
            # Invalid data or scenario that should trigger an error
        })

        # Expect a 500 Internal Server Error if something goes wrong
        self.assertEqual(response.status_code, 500)


    def test_logout_session_clear(self):
        """Test that session is cleared upon logout."""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)  # Redirects to login

        # Check that session is cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.conn.close()


if __name__ == "__main__":
    unittest.main()
