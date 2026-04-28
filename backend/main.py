import sys
import io
import os
import json

# 1. Force UTF-8 encoding for Windows consoles
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 2. Path resolution function for PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 3. Environment
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import tensorflow as tf
import numpy as np
from PIL import Image
from gtts import gTTS
import requests
import uvicorn

# ── Load .env (only in dev — ignored if not present) ─────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Auth imports (graceful fallback if not configured) ────────────────
AUTH_ENABLED = False
try:
    from auth     import (
        RegisterRequest, LoginRequest,
        register_user, login_user, refresh_token,
        get_current_user, get_optional_user,
    )
    from database import get_db
    AUTH_ENABLED = True
    print("✅ Auth + Database enabled")
except Exception as e:
    print(f"⚠️  Auth disabled (running without DB): {e}")

    # ── Dummy fallbacks so the rest of main.py compiles cleanly ──────
    class RegisterRequest(BaseModel):
        email: str; password: str; full_name: str
        phone: Optional[str] = None; village: Optional[str] = None
        district: Optional[str] = "Hyderabad"; state: Optional[str] = "Telangana"
        preferred_lang: Optional[str] = "te"

    class LoginRequest(BaseModel):
        email: str; password: str

    async def get_current_user():
        raise HTTPException(503, "Auth not configured.")

    async def get_optional_user():
        return None

    def get_db():
        return None

# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(title="CropDoc AI API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # necessary for file:// Electron origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ── Load classes ──────────────────────────────────────────────────────
try:
    json_path = resource_path('class_indices.json')
    with open(json_path, 'r') as f:
        data = json.load(f)

    if any(isinstance(v, int) for v in data.values()):
        lookup = {str(v): k for k, v in data.items()}
    else:
        lookup = {str(k): v for k, v in data.items()}

    CLASSES     = [lookup[str(i)] for i in range(len(lookup))]
    NUM_CLASSES = len(CLASSES)
    print(f"✅ Loaded {NUM_CLASSES} classes successfully.")

except Exception as e:
    print(f"❌ Error loading JSON: {e}")
    sys.exit(1)

# ── Load model ────────────────────────────────────────────────────────
print("Loading model...")
MODEL = None
for name in ["cropmodel_v2.h5", "cropmodel.h5"]:
    path = resource_path(name)
    if os.path.exists(path):
        MODEL = tf.keras.models.load_model(path)
        print(f"✅ Model loaded: {path} | Classes: {MODEL.output_shape[-1]}")
        break

if MODEL is None:
    print("❌ No model found!")
    sys.exit(1)

# ── Treatment database ────────────────────────────────────────────────
TREATMENTS = {
    "bacterial_spot": {
        "severity": "medium", "emoji": "🔬",
        "pesticide": "Copper Oxychloride 0.2% + Streptomycin 100ppm. Spray every 7 days.",
        "fertilizer": "Reduce nitrogen. Apply K₂SO₄ 2g/L.",
        "action": "Remove heavily infected leaves. Avoid overhead irrigation.",
        "tips": ["Use certified disease-free seeds","Disinfect tools with 1% bleach",
                 "Avoid working in wet field","Improve plant spacing"],
        "telugu": "బ్యాక్టీరియల్ స్పాట్ వ్యాధి. రాగి ఆక్సీక్లోరైడ్ పిచికారీ చేయండి.",
    },
    "early_blight": {
        "severity": "medium", "emoji": "🟡",
        "pesticide": "Mancozeb 0.2% or Chlorothalonil 2g/L. Spray every 10 days.",
        "fertilizer": "Balanced NPK 19:19:19. Add calcium nitrate 1g/L.",
        "action": "Remove lower infected leaves. Stake plants for airflow.",
        "tips": ["Water at base only","Apply straw mulch",
                 "Rotate crops yearly","Remove plant debris after harvest"],
        "telugu": "ఎర్లీ బ్లైట్ వ్యాధి. మాంకోజెబ్ మందు పిచికారీ చేయండి.",
    },
    "late_blight": {
        "severity": "critical", "emoji": "🚨",
        "pesticide": "RIDOMIL GOLD 0.2% IMMEDIATELY. Repeat in 5 days.",
        "fertilizer": "Stop nitrogen! Potassium + phosphorus only.",
        "action": "URGENT: Remove and BURN infected plants. Do NOT compost.",
        "tips": ["Spreads in 3 days if untreated","Spray entire field",
                 "Improve drainage","No evening irrigation"],
        "telugu": "లేట్ బ్లైట్ - అత్యంత ప్రమాదకరం! రిడోమిల్ గోల్డ్ వెంటనే పిచికారీ చేయండి.",
    },
    "leaf_mold": {
        "severity": "medium", "emoji": "🟤",
        "pesticide": "Chlorothalonil 0.2% or Copper hydroxide. Every 7-10 days.",
        "fertilizer": "Ensure adequate potassium. Reduce greenhouse humidity.",
        "action": "Improve ventilation. Remove affected leaves.",
        "tips": ["Open greenhouse vents","Never wet foliage",
                 "Space plants 45cm apart","Use resistant varieties"],
        "telugu": "లీఫ్ మోల్డ్ వ్యాధి. క్లోరోతలోనిల్ పిచికారీ చేయండి.",
    },
    "septoria": {
        "severity": "medium", "emoji": "🔴",
        "pesticide": "Chlorothalonil 0.2%. Spray every 7-14 days.",
        "fertilizer": "Balanced fertilization. Avoid excess nitrogen.",
        "action": "Remove infected leaves from base upwards.",
        "tips": ["Starts from lower leaves","Don't work in wet field",
                 "Stake plants","2-year crop rotation"],
        "telugu": "సెప్టోరియా లీఫ్ స్పాట్. రాగి ఆధారిత మందు పిచికారీ చేయండి.",
    },
    "spider_mites": {
        "severity": "medium", "emoji": "🕷️",
        "pesticide": "Abamectin 1ml/L or Neem oil 5ml/L + soap 2ml/L. Every 5 days × 3.",
        "fertilizer": "Maintain soil moisture. Silicon fertilizer helps.",
        "action": "Spray UNDER leaves where mites live.",
        "tips": ["Check underside of leaves","Increase humidity",
                 "Avoid killing natural predators","Yellow sticky traps help"],
        "telugu": "స్పైడర్ మైట్స్. అబమెక్టిన్ ఆకు కింద పిచికారీ చేయండి.",
    },
    "target_spot": {
        "severity": "medium", "emoji": "🎯",
        "pesticide": "Azoxystrobin 0.1% or Boscalid 0.15%. Every 10-14 days.",
        "fertilizer": "Reduce nitrogen. Increase calcium and potassium.",
        "action": "Remove infected leaves. Improve air circulation.",
        "tips": ["Common in warm humid weather","Remove fallen leaves",
                 "Adequate plant spacing","Avoid late evening irrigation"],
        "telugu": "టార్గెట్ స్పాట్ వ్యాధి. అజాక్సీస్ట్రోబిన్ పిచికారీ చేయండి.",
    },
    "ylcv": {
        "severity": "critical", "emoji": "🚨",
        "pesticide": "Control whitefly: Imidacloprid 0.3ml/L. Every 5 days.",
        "fertilizer": "Zinc sulfate 0.5g/L + Boron 0.2g/L foliar spray.",
        "action": "Remove and BURN infected plants. Kill all whiteflies.",
        "tips": ["Whiteflies spread this virus","Yellow sticky traps",
                 "Silver mulch repels whiteflies","Use resistant varieties"],
        "telugu": "పసుపు ఆకు మురి వైరస్! తెల్ల దోమలను నిర్మూలించండి.",
    },
    "mosaic_virus": {
        "severity": "critical", "emoji": "🦠",
        "pesticide": "Control aphids: Dimethoate 0.05% or Imidacloprid 0.3ml/L.",
        "fertilizer": "Balanced nutrition. Avoid excess nitrogen.",
        "action": "Remove infected plants. Disinfect hands and tools immediately.",
        "tips": ["Spreads by touch","Wash hands between plants",
                 "Use certified seeds","10% bleach disinfects tools"],
        "telugu": "మొజాయిక్ వైరస్. సోకిన మొక్కలను తక్షణమే తొలగించండి.",
    },
    "healthy": {
        "severity": "none", "emoji": "✅",
        "pesticide": "No treatment needed.",
        "fertilizer": "Continue NPK 19:19:19 every 15 days.",
        "action": "Plant is healthy! Monitor every 7 days.",
        "tips": ["Regular monitoring","Proper irrigation",
                 "Good air circulation","Keep field weed-free"],
        "telugu": "మొక్క ఆరోగ్యంగా ఉంది! నిత్య పర్యవేక్షణ కొనసాగించండి.",
    },
}

def get_treatment(class_name: str) -> dict:
    n = class_name.lower()
    if "healthy"   in n: return {**TREATMENTS["healthy"],       "title": "Healthy Plant ✅"}
    if "late"      in n: return {**TREATMENTS["late_blight"],   "title": "Late Blight 🚨"}
    if "early"     in n: return {**TREATMENTS["early_blight"],  "title": "Early Blight"}
    if "bacterial" in n: return {**TREATMENTS["bacterial_spot"],"title": "Bacterial Spot"}
    if "mold"      in n: return {**TREATMENTS["leaf_mold"],     "title": "Leaf Mold"}
    if "septoria"  in n: return {**TREATMENTS["septoria"],      "title": "Septoria Leaf Spot"}
    if "spider"    in n: return {**TREATMENTS["spider_mites"],  "title": "Spider Mites"}
    if "target"    in n: return {**TREATMENTS["target_spot"],   "title": "Target Spot"}
    if "yellow" in n or "curl" in n:
                         return {**TREATMENTS["ylcv"],          "title": "Yellow Leaf Curl Virus 🚨"}
    if "mosaic"    in n: return {**TREATMENTS["mosaic_virus"],  "title": "Mosaic Virus 🦠"}
    return {
        "severity": "unknown", "emoji": "❓",
        "title":     class_name.replace("_", " ").title(),
        "pesticide": "Consult agriculture officer",
        "fertilizer":"Get soil test done",
        "action":    "Visit nearest Krishi Vigyan Kendra",
        "tips":      ["Monitor closely", "Photograph symptoms daily"],
        "telugu":    "వ్యవసాయ అధికారిని సంప్రదించండి.",
    }

# ═══════════════════════════════════════════════════════════════════════
#  EXISTING ROUTES — UNCHANGED
# ═══════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "CropDoc AI running", "classes": NUM_CLASSES}

@app.get("/health")
def health():
    return {
        "status":       "ok",
        "model_loaded": MODEL is not None,
        "num_classes":  NUM_CLASSES,
        "auth_enabled": AUTH_ENABLED,
    }

@app.get("/classes")
def get_classes():
    return {"classes": CLASSES, "count": NUM_CLASSES}

# ── Weather ───────────────────────────────────────────────────────────
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "60e1c8df454931f0ce73026aa1165489")

@app.get("/weather")
async def get_weather(lat: float, lon: float):
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    )
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail="Weather data fetch failed"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Market prices ─────────────────────────────────────────────────────
MARKET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
MARKET_API_KEY     = os.getenv(
    "MARKET_API_KEY",
    "579b464db66ec23bdd000001c67bccb742b442ca7791f3db9f440548"
)

@app.get("/market-prices")
async def get_market_prices(
    commodity: str = None,
    state:     str = None,
    limit:     int = 100
):
    url = (
        f"https://api.data.gov.in/resource/{MARKET_RESOURCE_ID}"
        f"?api-key={MARKET_API_KEY}&format=json&limit={limit}"
    )
    if commodity:
        url += f"&filters[commodity]={commodity}"
    if state:
        url += f"&filters[state]={state}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("records", [])
        print(f"API Error: {response.status_code} - {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to fetch Mandi data"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Predict ───────────────────────────────────────────────────────────
@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    # optional auth — works with or without login
    current_user: Optional[dict] = Depends(get_optional_user) if AUTH_ENABLED else None,
):
    if MODEL is None:
        raise HTTPException(503, "Model not loaded")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    contents = await file.read()
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 15MB)")

    img   = Image.open(io.BytesIO(contents)).convert('RGB').resize((224, 224))
    arr   = np.array(img, dtype=np.float32)
    arr   = tf.keras.applications.efficientnet.preprocess_input(arr)
    arr   = np.expand_dims(arr, axis=0)
    probs = MODEL.predict(arr, verbose=0)[0]

    idx        = int(np.argmax(probs))
    confidence = float(probs[idx]) * 100
    class_name = CLASSES[idx]
    treatment  = get_treatment(class_name)

    top5 = [
        {
            "class":      CLASSES[i],
            "label":      CLASSES[i].replace("___"," ").replace("__"," ").replace("_"," ").title(),
            "confidence": round(float(probs[i]) * 100, 2),
        }
        for i in np.argsort(probs)[::-1][:5]
        if i < len(CLASSES)
    ]

    response = {
        "class_name":   class_name,
        "display_name": treatment["title"],
        "confidence":   round(confidence, 2),
        "severity":     treatment["severity"],
        "emoji":        treatment["emoji"],
        "pesticide":    treatment["pesticide"],
        "fertilizer":   treatment["fertilizer"],
        "action":       treatment["action"],
        "tips":         treatment["tips"],
        "telugu":       treatment["telugu"],
        "top5":         top5,
        "saved_to_history": False,
    }

    # ── Save to DB if user is logged in ───────────────────────────────
    if AUTH_ENABLED and current_user:
        try:
            db   = get_db()
            crop = (
                "Tomato" if "tomato" in class_name.lower() else
                "Potato" if "potato" in class_name.lower() else
                "Pepper" if "pepper" in class_name.lower() else
                "Unknown"
            )
            db.table("predictions").insert({
                "user_id":          current_user["id"],
                "disease_name":     class_name,
                "display_name":     treatment["title"],
                "confidence":       round(confidence, 2),
                "severity":         treatment["severity"],
                "crop_type":        crop,
                "pesticide":        treatment["pesticide"],
                "fertilizer":       treatment["fertilizer"],
                "location_village": current_user.get("village"),
            }).execute()
            response["saved_to_history"] = True
        except Exception as e:
            print(f"⚠️  DB save warning: {e}")

    return response

# ── TTS ───────────────────────────────────────────────────────────────
@app.get("/speak")
def speak(text: str, lang: str = "te"):
    valid_langs = {"te": "te", "hi": "hi", "en": "en"}
    lang = valid_langs.get(lang, "te")
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(500, f"TTS error: {e}")

# ═══════════════════════════════════════════════════════════════════════
#  NEW AUTH ROUTES — only active when AUTH_ENABLED = True
# ═══════════════════════════════════════════════════════════════════════

if AUTH_ENABLED:

    class RefreshRequest(BaseModel):
        refresh_token: str

    class UpdateProfileRequest(BaseModel):
        full_name:      Optional[str] = None
        phone:          Optional[str] = None
        village:        Optional[str] = None
        district:       Optional[str] = None
        preferred_lang: Optional[str] = None

    @app.post("/register")
    async def register(data: RegisterRequest):
        """Register new farmer — Supabase Auth sends confirmation email."""
        return await register_user(data)

    @app.post("/login")
    async def login(data: LoginRequest):
        """Login — returns Supabase JWT verified via JWKS."""
        return await login_user(data)

    @app.post("/refresh")
    async def refresh(data: RefreshRequest):
        """Refresh expired access token."""
        return await refresh_token(data.refresh_token)

    @app.get("/me")
    async def get_me(current_user: dict = Depends(get_current_user)):
        """Get current user profile."""
        db      = get_db()
        profile = db.table("farmer_profiles") \
                    .select("*") \
                    .eq("user_id", current_user["id"]) \
                    .execute()
        return {
            "user":    {k: v for k, v in current_user.items()
                        if k != "token_payload"},
            "profile": profile.data[0] if profile.data else {},
        }

    @app.put("/me")
    async def update_profile(
        data:         UpdateProfileRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """Update profile fields."""
        db      = get_db()
        updates = {k: v for k, v in data.dict().items() if v is not None}
        if updates:
            db.table("profiles") \
              .update(updates) \
              .eq("id", current_user["id"]) \
              .execute()
        return {"message": "Profile updated.", "updated": updates}

    @app.get("/history")
    async def get_history(
        limit:        int  = 20,
        current_user: dict = Depends(get_current_user)
    ):
        """Get prediction history for logged-in user."""
        db     = get_db()
        result = db.table("predictions") \
                   .select("*") \
                   .eq("user_id", current_user["id"]) \
                   .order("created_at", desc=True) \
                   .limit(limit) \
                   .execute()
        return {"predictions": result.data, "count": len(result.data)}

    @app.delete("/history/{prediction_id}")
    async def delete_prediction(
        prediction_id: str,
        current_user:  dict = Depends(get_current_user)
    ):
        """Delete a specific prediction."""
        db = get_db()
        db.table("predictions") \
          .delete() \
          .eq("id",      prediction_id) \
          .eq("user_id", current_user["id"]) \
          .execute()
        return {"message": "Deleted."}

    @app.get("/jwks-test")
    async def test_jwks():
        """Verify JWKS is reachable — dev diagnostic endpoint."""
        from auth import get_jwks
        jwks = get_jwks()
        return {
            "status":   "ok",
            "jwks_url": os.getenv("SUPABASE_JWKS_URL"),
            "num_keys": len(jwks.get("keys", [])),
            "key_ids":  [k.get("kid") for k in jwks.get("keys", [])],
        }

# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
        log_level="info",
        use_colors=False,
    )