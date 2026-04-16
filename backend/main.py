# backend/main.py
import os, json, io
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import tensorflow as tf
import numpy as np
from PIL import Image
from gtts import gTTS
import uvicorn

app = FastAPI(title="CropDoc AI API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load classes ──────────────────────────────────────────────────────
with open("class_indices.json") as f:
    d = json.load(f)
CLASSES = [d[str(i)] for i in range(len(d))]
NUM_CLASSES = len(CLASSES)

# ── Load model once at startup ────────────────────────────────────────
print("Loading model...")
MODEL = None
for path in ["cropmodel_v2.h5", "cropmodel.h5"]:
    if os.path.exists(path):
        MODEL = tf.keras.models.load_model(path)
        print(f"✅ Model loaded: {path} | Classes: {MODEL.output_shape[-1]}")
        break

if MODEL is None:
    print("❌ No model found!")

# ── Treatment database ────────────────────────────────────────────────
TREATMENTS = {
    "bacterial_spot": {
        "severity": "medium", "emoji": "🔬",
        "pesticide": "Copper Oxychloride 0.2% + Streptomycin 100ppm. Spray every 7 days.",
        "fertilizer": "Reduce nitrogen. Apply K₂SO₄ 2g/L.",
        "action": "Remove heavily infected leaves. Avoid overhead irrigation.",
        "tips": ["Use certified disease-free seeds","Disinfect tools with 1% bleach","Avoid working in wet field","Improve plant spacing"],
        "telugu": "బ్యాక్టీరియల్ స్పాట్ వ్యాధి. రాగి ఆక్సీక్లోరైడ్ పిచికారీ చేయండి.",
    },
    "early_blight": {
        "severity": "medium", "emoji": "🟡",
        "pesticide": "Mancozeb 0.2% or Chlorothalonil 2g/L. Spray every 10 days.",
        "fertilizer": "Balanced NPK 19:19:19. Add calcium nitrate 1g/L.",
        "action": "Remove lower infected leaves. Stake plants for airflow.",
        "tips": ["Water at base only","Apply straw mulch","Rotate crops yearly","Remove plant debris after harvest"],
        "telugu": "ఎర్లీ బ్లైట్ వ్యాధి. మాంకోజెబ్ మందు పిచికారీ చేయండి.",
    },
    "late_blight": {
        "severity": "critical", "emoji": "🚨",
        "pesticide": "RIDOMIL GOLD 0.2% IMMEDIATELY. Repeat in 5 days.",
        "fertilizer": "Stop nitrogen! Potassium + phosphorus only.",
        "action": "URGENT: Remove and BURN infected plants. Do NOT compost.",
        "tips": ["Spreads in 3 days if untreated","Spray entire field","Improve drainage","No evening irrigation"],
        "telugu": "లేట్ బ్లైట్ - అత్యంత ప్రమాదకరం! రిడోమిల్ గోల్డ్ వెంటనే పిచికారీ చేయండి.",
    },
    "leaf_mold": {
        "severity": "medium", "emoji": "🟤",
        "pesticide": "Chlorothalonil 0.2% or Copper hydroxide. Every 7-10 days.",
        "fertilizer": "Ensure adequate potassium. Reduce greenhouse humidity.",
        "action": "Improve ventilation. Remove affected leaves.",
        "tips": ["Open greenhouse vents","Never wet foliage","Space plants 45cm apart","Use resistant varieties"],
        "telugu": "లీఫ్ మోల్డ్ వ్యాధి. క్లోరోతలోనిల్ పిచికారీ చేయండి.",
    },
    "septoria": {
        "severity": "medium", "emoji": "🔴",
        "pesticide": "Chlorothalonil 0.2%. Spray every 7-14 days.",
        "fertilizer": "Balanced fertilization. Avoid excess nitrogen.",
        "action": "Remove infected leaves from base upwards.",
        "tips": ["Starts from lower leaves","Don't work in wet field","Stake plants","2-year crop rotation"],
        "telugu": "సెప్టోరియా లీఫ్ స్పాట్. రాగి ఆధారిత మందు పిచికారీ చేయండి.",
    },
    "spider_mites": {
        "severity": "medium", "emoji": "🕷️",
        "pesticide": "Abamectin 1ml/L or Neem oil 5ml/L + soap 2ml/L. Every 5 days × 3.",
        "fertilizer": "Maintain soil moisture. Silicon fertilizer helps.",
        "action": "Spray UNDER leaves where mites live.",
        "tips": ["Check underside of leaves","Increase humidity","Avoid killing natural predators","Yellow sticky traps help"],
        "telugu": "స్పైడర్ మైట్స్. అబమెక్టిన్ ఆకు కింద పిచికారీ చేయండి.",
    },
    "target_spot": {
        "severity": "medium", "emoji": "🎯",
        "pesticide": "Azoxystrobin 0.1% or Boscalid 0.15%. Every 10-14 days.",
        "fertilizer": "Reduce nitrogen. Increase calcium and potassium.",
        "action": "Remove infected leaves. Improve air circulation.",
        "tips": ["Common in warm humid weather","Remove fallen leaves","Adequate plant spacing","Avoid late evening irrigation"],
        "telugu": "టార్గెట్ స్పాట్ వ్యాధి. అజాక్సీస్ట్రోబిన్ పిచికారీ చేయండి.",
    },
    "ylcv": {
        "severity": "critical", "emoji": "🚨",
        "pesticide": "Control whitefly: Imidacloprid 0.3ml/L. Every 5 days.",
        "fertilizer": "Zinc sulfate 0.5g/L + Boron 0.2g/L foliar spray.",
        "action": "Remove and BURN infected plants. Kill all whiteflies.",
        "tips": ["Whiteflies spread this virus","Yellow sticky traps","Silver mulch repels whiteflies","Use resistant varieties"],
        "telugu": "పసుపు ఆకు మురి వైరస్! తెల్ల దోమలను నిర్మూలించండి.",
    },
    "mosaic_virus": {
        "severity": "critical", "emoji": "🦠",
        "pesticide": "Control aphids: Dimethoate 0.05% or Imidacloprid 0.3ml/L.",
        "fertilizer": "Balanced nutrition. Avoid excess nitrogen.",
        "action": "Remove infected plants. Disinfect hands and tools immediately.",
        "tips": ["Spreads by touch","Wash hands between plants","Use certified seeds","10% bleach disinfects tools"],
        "telugu": "మొజాయిక్ వైరస్. సోకిన మొక్కలను తక్షణమే తొలగించండి.",
    },
    "healthy": {
        "severity": "none", "emoji": "✅",
        "pesticide": "No treatment needed.",
        "fertilizer": "Continue NPK 19:19:19 every 15 days.",
        "action": "Plant is healthy! Monitor every 7 days.",
        "tips": ["Regular monitoring","Proper irrigation","Good air circulation","Keep field weed-free"],
        "telugu": "మొక్క ఆరోగ్యంగా ఉంది! నిత్య పర్యవేక్షణ కొనసాగించండి.",
    },
}

def get_treatment(class_name: str) -> dict:
    n = class_name.lower()
    if "healthy"   in n: return {**TREATMENTS["healthy"],   "title": "Healthy Plant ✅"}
    if "late"      in n: return {**TREATMENTS["late_blight"],"title": "Late Blight 🚨"}
    if "early"     in n: return {**TREATMENTS["early_blight"],"title": "Early Blight"}
    if "bacterial" in n: return {**TREATMENTS["bacterial_spot"],"title": "Bacterial Spot"}
    if "mold"      in n: return {**TREATMENTS["leaf_mold"],  "title": "Leaf Mold"}
    if "septoria"  in n: return {**TREATMENTS["septoria"],   "title": "Septoria Leaf Spot"}
    if "spider"    in n: return {**TREATMENTS["spider_mites"],"title": "Spider Mites"}
    if "target"    in n: return {**TREATMENTS["target_spot"],"title": "Target Spot"}
    if "yellow" in n or "curl" in n: return {**TREATMENTS["ylcv"], "title": "Yellow Leaf Curl Virus 🚨"}
    if "mosaic"    in n: return {**TREATMENTS["mosaic_virus"],"title": "Mosaic Virus 🦠"}
    return {
        "severity": "unknown", "emoji": "❓",
        "title": class_name.replace("_"," ").title(),
        "pesticide": "Consult agriculture officer",
        "fertilizer": "Get soil test done",
        "action": "Visit nearest Krishi Vigyan Kendra",
        "tips": ["Monitor closely", "Photograph symptoms daily"],
        "telugu": "వ్యవసాయ అధికారిని సంప్రదించండి.",
    }

# ── API Routes ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "CropDoc AI running", "classes": NUM_CLASSES}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
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
        {"class": CLASSES[i], "label": CLASSES[i].replace("___"," ").replace("__"," ").replace("_"," ").title(), "confidence": round(float(probs[i]) * 100, 2)}
        for i in np.argsort(probs)[::-1][:5]
        if i < len(CLASSES)
    ]

    return {
        "class_name":    class_name,
        "display_name":  treatment["title"],
        "confidence":    round(confidence, 2),
        "severity":      treatment["severity"],
        "emoji":         treatment["emoji"],
        "pesticide":     treatment["pesticide"],
        "fertilizer":    treatment["fertilizer"],
        "action":        treatment["action"],
        "tips":          treatment["tips"],
        "telugu":        treatment["telugu"],
        "top5":          top5,
    }

@app.get("/speak")
def speak(text: str, lang: str = "te"):
    """Convert text to speech, stream MP3."""
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

@app.get("/classes")
def get_classes():
    return {"classes": CLASSES, "count": NUM_CLASSES}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "num_classes": NUM_CLASSES,
    }

# ── REPLACE WITH THIS ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import uvicorn

    # Windows-safe way to run uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,       # ← False fixes the signal error on Windows
        workers=1,
    )