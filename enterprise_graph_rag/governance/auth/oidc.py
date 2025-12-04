import os
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from governance.auth.models import UserIdentity
from knowledge_engine.core.logging import logger

class OIDCAuthenticator:
    """
    Validates JWT tokens from an Identity Provider (Okta, Azure AD).
    For Development, it accepts a "mock" token if ENV is set to DEV.
    """
    security = HTTPBearer()
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.environment = os.getenv("ENVIRONMENT", "dev")

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> UserIdentity:
        token = credentials.credentials
        
        try:
            # 1. Decode Token
            # In Prod: fetch JWKS from OIDC provider to verify signature
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 2. Extract Claims
            user_id: str = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Token missing subject")
                
            # 3. Construct Identity
            identity = UserIdentity(
                user_id=user_id,
                email=payload.get("email", ""),
                department=payload.get("department", "general"),
                roles=payload.get("roles", [])
            )
            return identity

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

# Singleton
authenticator = OIDCAuthenticator()