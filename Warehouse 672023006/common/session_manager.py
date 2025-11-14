import jwt
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self):
        self.secret = "Dreamyyy245_"
        
    def generate_token(self, username, role):
        payload = {
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        try:
            return jwt.encode(payload, self.secret, algorithm="HS256")
        except Exception as e:
            print(f"Error generating token: {str(e)}")
            return None
        
    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            return {
                "username": payload.get("username", ""),
                "role": payload.get("role", "")
            }
        except jwt.ExpiredSignatureError:
            print("Token expired")
            return None
        except Exception as e:
            print(f"Error verifying token: {str(e)}")
            return None
