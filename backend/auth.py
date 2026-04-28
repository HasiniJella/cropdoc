# backend/auth.py — JWKS version
import os
import json
import httpx
import jwt as pyjwt

from datetime  import datetime
from typing    import Optional
from functools import lru_cache

from fastapi                import Depends, HTTPException, status
from fastapi.security       import HTTPBearer, HTTPAuthorizationCredentials
from pydantic               import BaseModel
from database               import get_db

# ── Config ────────────────────────────────────────────────────────────
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
JWKS_URL          = os.getenv(
    "SUPABASE_JWKS_URL",
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
)

bearer_scheme = HTTPBearer(auto_error=False)

# ── Pydantic request models ───────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:          str
    password:       str
    full_name:      str
    phone:          Optional[str] = None
    village:        Optional[str] = None
    district:       Optional[str] = "Hyderabad"
    state:          Optional[str] = "Telangana"
    preferred_lang: Optional[str] = "te"

class LoginRequest(BaseModel):
    email:    str
    password: str

class UpdateProfileRequest(BaseModel):
    full_name:      Optional[str] = None
    phone:          Optional[str] = None
    village:        Optional[str] = None
    district:       Optional[str] = None
    preferred_lang: Optional[str] = None

# ── JWKS key fetching and caching ─────────────────────────────────────
_jwks_cache: Optional[dict] = None
_jwks_fetched_at: Optional[datetime] = None

def get_jwks() -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Supabase.
    Cache for 1 hour to avoid hitting the endpoint on every request.
    """
    global _jwks_cache, _jwks_fetched_at

    now = datetime.utcnow()

    # Return cached keys if fetched within last hour
    if (
        _jwks_cache
        and _jwks_fetched_at
        and (now - _jwks_fetched_at).seconds < 3600
    ):
        return _jwks_cache

    try:
        print(f"🔑 Fetching JWKS from: {JWKS_URL}")
        response = httpx.get(JWKS_URL, timeout=10.0)
        response.raise_for_status()
        _jwks_cache     = response.json()
        _jwks_fetched_at = now
        print(f"✅ JWKS fetched — {len(_jwks_cache.get('keys', []))} keys")
        return _jwks_cache
    except Exception as e:
        print(f"❌ JWKS fetch failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable. Could not fetch JWKS."
        )

def get_public_key(kid: Optional[str] = None):
    """
    Get the RSA public key from JWKS for token verification.
    If kid (key ID) provided, find matching key. Otherwise use first key.
    """
    jwks = get_jwks()
    keys = jwks.get("keys", [])

    if not keys:
        raise HTTPException(status_code=503, detail="No public keys available.")

    if kid:
        # Find key matching the kid in token header
        for key_data in keys:
            if key_data.get("kid") == kid:
                return pyjwt.algorithms.RSAAlgorithm.from_jwk(
                    json.dumps(key_data)
                )
        # If kid not found, try first key (fallback)
        print(f"⚠️  kid '{kid}' not found in JWKS, using first key")

    return pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[0]))

# ── JWT verification via JWKS ─────────────────────────────────────────
def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase-issued JWT using the JWKS public key.
    Returns decoded payload if valid.
    """
    try:
        # Decode header first to get kid (key ID)
        unverified_header = pyjwt.get_unverified_header(token)
        kid               = unverified_header.get("kid")

        # Get matching public key
        public_key = get_public_key(kid)

        # Verify and decode the token
        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256"],        # Supabase uses RS256
            audience="authenticated",    # Supabase sets this audience
            options={
                "verify_exp":      True,
                "verify_aud":      True,
                "require":         ["sub", "exp", "aud"],
            }
        )
        return payload

    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ── FastAPI dependency — get current user ─────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Dependency that verifies JWT via JWKS and returns the user
    from our profiles table.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token using Supabase JWKS
    payload = verify_supabase_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID."
        )

    # Fetch profile from our database
    db     = get_db()
    result = db.table("profiles").select("*").eq("id", user_id).execute()

    if not result.data:
        # Profile not yet created — create it now
        try:
            db.table("profiles").insert({"id": user_id}).execute()
            db.table("farmer_profiles").insert({"user_id": user_id}).execute()
            result = db.table("profiles").select("*").eq("id", user_id).execute()
        except Exception:
            pass

    profile = result.data[0] if result.data else {}

    return {
        "id":             user_id,
        "email":          payload.get("email", ""),
        "full_name":      profile.get("full_name", "Farmer"),
        "phone":          profile.get("phone"),
        "village":        profile.get("village"),
        "district":       profile.get("district", "Hyderabad"),
        "state":          profile.get("state", "Telangana"),
        "preferred_lang": profile.get("preferred_lang", "te"),
        "token_payload":  payload,
    }

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> Optional[dict]:
    """Returns user if token provided and valid, None otherwise."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# ── Auth handlers — delegate to Supabase Auth ─────────────────────────
async def register_user(data: RegisterRequest) -> dict:
    """
    Register using Supabase Auth.
    Supabase sends OTP/confirmation email automatically.
    """
    db = get_db()

    try:
        # Use Supabase Auth to create user
        result = db.auth.sign_up({
            "email":    data.email.lower().strip(),
            "password": data.password,
            "options": {
                "data": {
                    "full_name":      data.full_name.strip(),
                    "phone":          data.phone or "",
                    "village":        data.village or "",
                    "district":       data.district,
                    "preferred_lang": data.preferred_lang,
                }
            }
        })

        if not result.user:
            raise HTTPException(status_code=400, detail="Registration failed.")

        # Update our profiles table with extra fields
        db.table("profiles").upsert({
            "id":             result.user.id,
            "full_name":      data.full_name.strip(),
            "phone":          data.phone,
            "village":        data.village,
            "district":       data.district,
            "state":          data.state,
            "preferred_lang": data.preferred_lang,
        }).execute()

        return {
            "message": (
                f"Registration successful! "
                f"A confirmation email has been sent to {data.email}. "
                f"Please verify your email before logging in."
            ),
            "user_id": result.user.id,
            "email":   result.user.email,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Email already registered.")
        raise HTTPException(status_code=500, detail=f"Registration error: {error_msg}")

async def login_user(data: LoginRequest) -> dict:
    """
    Login using Supabase Auth.
    Returns Supabase JWT — verified via JWKS on subsequent requests.
    """
    db = get_db()

    try:
        result = db.auth.sign_in_with_password({
            "email":    data.email.lower().strip(),
            "password": data.password,
        })

        if not result.user or not result.session:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        # Fetch profile
        profile = db.table("profiles") \
                    .select("*") \
                    .eq("id", result.user.id) \
                    .execute()

        profile_data = profile.data[0] if profile.data else {}

        return {
            "access_token":  result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "token_type":    "bearer",
            "expires_in":    result.session.expires_in,
            "user": {
                "id":             result.user.id,
                "email":          result.user.email,
                "full_name":      profile_data.get("full_name", "Farmer"),
                "phone":          profile_data.get("phone"),
                "village":        profile_data.get("village"),
                "district":       profile_data.get("district", "Hyderabad"),
                "preferred_lang": profile_data.get("preferred_lang", "te"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if "email not confirmed" in error_msg:
            raise HTTPException(
                status_code=403,
                detail="Please confirm your email before logging in. Check your inbox."
            )
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

async def refresh_token(refresh_token: str) -> dict:
    """Refresh an expired access token using the refresh token."""
    db = get_db()
    try:
        result = db.auth.refresh_session(refresh_token)
        if not result.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token.")
        return {
            "access_token":  result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "token_type":    "bearer",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token refresh failed.")