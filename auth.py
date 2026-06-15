"""
Sample Authentication Module
Demonstrates password hashing, token generation, and user authentication.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple


class PasswordManager:
    """Handles password hashing and verification using PBKDF2."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash a password using PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(32)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${hash_obj.hex()}"
    
    @staticmethod
    def verify_password(password: str, hash_value: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, _ = hash_value.split('$')
            new_hash = PasswordManager.hash_password(password, salt)
            return hmac.compare_digest(hash_value, new_hash)
        except ValueError:
            return False


class JWTTokenManager:
    """Generates and validates JWT tokens."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_token(self, user_id: str, expires_in_hours: int = 24) -> str:
        """Generate a JWT token with expiration."""
        import base64
        
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "user_id": user_id,
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp()
        }
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Create signature
        message = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(
            self.secret_key.encode(),
            message,
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate and decode a JWT token."""
        import base64
        
        try:
            header_b64, payload_b64, signature_b64 = token.split('.')
            
            # Verify signature
            message = f"{header_b64}.{payload_b64}".encode()
            expected_signature = base64.urlsafe_b64encode(
                hmac.new(
                    self.secret_key.encode(),
                    message,
                    hashlib.sha256
                ).digest()
            ).decode().rstrip('=')
            
            if not hmac.compare_digest(signature_b64, expected_signature):
                return None
            
            # Decode payload
            padding = 4 - (len(payload_b64) % 4)
            payload_b64 += '=' * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            
            # Check expiration
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                return None
            
            return payload
        except (ValueError, json.JSONDecodeError):
            return None


class UserAuthenticator:
    """Manages user authentication with credentials storage."""
    
    def __init__(self, secret_key: str):
        self.users = {}  # In production, use a database
        self.token_manager = JWTTokenManager(secret_key)
        self.password_manager = PasswordManager()
    
    def register_user(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        """Register a new user."""
        if username in self.users:
            return False, "Username already exists"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        self.users[username] = {
            "password_hash": self.password_manager.hash_password(password),
            "email": email,
            "created_at": datetime.utcnow().isoformat()
        }
        return True, "User registered successfully"
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user and return token."""
        if username not in self.users:
            return False, "Invalid credentials"
        
        user = self.users[username]
        if not self.password_manager.verify_password(password, user["password_hash"]):
            return False, "Invalid credentials"
        
        token = self.token_manager.generate_token(username)
        return True, token
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """Validate a token and return user_id."""
        payload = self.token_manager.validate_token(token)
        if payload:
            return True, payload.get("user_id")
        return False, None


# Example usage
if __name__ == "__main__":
    # Initialize authenticator
    auth = UserAuthenticator(secret_key="your-secret-key-change-in-production")
    
    # Register a user
    print("=== User Registration ===")
    success, message = auth.register_user("john_doe", "SecurePass123", "john@example.com")
    print(f"Registration: {message}")
    
    # Login
    print("\n=== User Login ===")
    success, token = auth.login("john_doe", "SecurePass123")
    if success:
        print(f"Login successful!")
        print(f"Token: {token[:20]}...")
    else:
        print(f"Login failed: {token}")
    
    # Validate token
    print("\n=== Token Validation ===")
    valid, user_id = auth.validate_token(token)
    print(f"Token valid: {valid}, User ID: {user_id}")
    
    # Test with invalid credentials
    print("\n=== Invalid Login ===")
    success, message = auth.login("john_doe", "WrongPassword")
    print(f"Result: {message}")
