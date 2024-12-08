import random
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
import sqlite3

# Load environment variables
load_dotenv()


class OTPVerifier:
    def __init__(self, app):
        self.app = app
        self.otp_data = {}
        self.mail = Mail(app)

    def generate_otp(self, user_id):
        """Generate a random 6-digit OTP"""
        otp = random.randint(100000, 999999)
        self.otp_data[user_id] = otp
        return otp

    def send_otp_email(self, email, otp, subject):
        """Send OTP to the user's email"""
        try:
            msg = Message(subject,
                          sender=os.getenv('EMAIL_USER'),
                          recipients=[email],
                          body=f"Your OTP code is: {otp}")
            self.mail.send(msg)  # Send the OTP email
            print(f"OTP sent to {email}!")  # Debugging output
        except Exception as e:
            raise Exception(f"Error sending email: {e}")

    def validate_otp(self, user_id, input_otp):
        """Validate the OTP entered by the user"""
        if self.otp_data.get(user_id) == input_otp:
            return True, "OTP Verified successfully."
        else:
            return False, "Invalid OTP. Please try again."

    # Email verification part (existing)
    def send_verification_email(self, email, user_id):
        """Send email verification with OTP"""
        otp = self.generate_otp(user_id)  # Generate OTP for email verification
        self.send_otp_email(email, otp, subject="Email Verification OTP")
        return otp  # Returning OTP for possible use in other parts of the system

    def verify_email_otp(self, user_id, input_otp):
        """Verify the OTP entered by the user for email verification"""
        return self.validate_otp(user_id, input_otp)

    # Forgot password part (new)
    def send_password_reset_email(self, email, user_id):
        """Send password reset OTP"""
        otp = self.generate_otp(user_id)  # Generate OTP for password reset
        self.send_otp_email(email, otp, subject="Password Reset OTP")
        return otp  # Returning OTP for further use

    def verify_password_reset_otp(self, user_id, input_otp):
        """Verify the OTP entered by the user for password reset"""
        return self.validate_otp(user_id, input_otp)
