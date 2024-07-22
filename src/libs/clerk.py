import os
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError


class Clerk:
    def __init__(self):
        clerk_domain = os.getenv('CLERK_DOMAIN')
        if not clerk_domain:
            raise ValueError("CLERK_DOMAIN environment variable is missing")
        self.jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
        self.issuer = f"https://{clerk_domain}"
        self.jwk_client = jwt.PyJWKClient(self.jwks_url)

    async def get_signing_key(self, token):
        signing_key = self.jwk_client.get_signing_key_from_jwt(token)
        return signing_key.key

    async def get_user_id(self, token):
        try:
            signing_key = await self.get_signing_key(token)

            # Decode and verify the token
            decoded_token = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=None,  # Add your audience if you have one
                issuer=self.issuer
            )

            # Extract and return the user ID
            user_id = decoded_token.get('sub')
            if not user_id:
                raise ValueError("User ID (sub) not found in token")

            return user_id
        except ExpiredSignatureError:
            raise ValueError("Token has expired")
        except InvalidTokenError:
            raise ValueError("Invalid token")
