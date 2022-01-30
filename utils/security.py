from cryptography.hazmat.primitives import serialization
import jwt


class SecurityClient:
    def __init__(self, private_key, password):
        self.key = serialization.load_ssh_private_key(
            open(private_key, "r").read().encode(), password=password.encode()
        )

    def encryptPayload(self, payload):
        return jwt.encode(payload=payload, key=self.key, algorithm="RS256")
