
from dataclasses import dataclass
from pydantic import BaseModel

class LoginSchema(BaseModel):
    username: str
    password: str

    def validate_username(self):
        if not self.username:
            return ValueError("Username is required")
