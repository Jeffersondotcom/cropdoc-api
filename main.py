from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CLASS_NAMES = [
    "Corn - Cercospora Leaf Spot",
    "Corn - Common Rust",
    "Corn - Northern Leaf Blight",
    "Corn - Healthy",
    "Pepper - Bacterial Spot",
    "Pepper - Healthy",
    "Potato - Early Blight",
    "Potato - Late Blight",
    "Potato - Healthy",
    "Tomato - Bacterial Spot",
    "Tomato - Early Blight",
    "Tomato - Late Blight",
    "Tomato - Leaf Mold",
    "Tomato - Septoria Leaf Spot",
    "Tomato - Spider Mites",
    "Tomato - Target Spot",
    "Tomato - Yellow Leaf Curl Virus",
    "Tomato - Mosaic Virus",
    "Tomato - Healthy",
]

TREATMENTS = {
    "Corn - Cercospora Leaf Spot": "Apply fungicides containing azoxystrobin or pyraclostrobin. Remove infected leaves.",
    "Corn - Common Rust": "Apply fungicides early. Plant resistant varieties next season.",
    "Corn - Northern Leaf Blight": "Apply mancozeb-based fungicide. Rotate crops next season.",
    "Corn - Healthy": "No treatment needed. Crop is healthy.",
    "Pepper - Bacterial Spot": "Apply copper-based bactericide. Avoid overhead irrigation.",
    "Pepper - Healthy": "No treatment needed. Crop is healthy.",
    "Potato - Early Blight": "Apply chlorothalonil fungicide. Remove infected leaves immediately.",
    "Potato - Late Blight": "Apply metalaxyl fungicide immediately. This spreads fast.",
    "Potato - Healthy": "No treatment needed. Crop is healthy.",
    "Tomato - Bacterial Spot": "Apply copper hydroxide spray. Remove and destroy infected plants.",
    "Tomato - Early Blight": "Apply mancozeb fungicide. Mulch around base of plants.",
    "Tomato - Late Blight": "Apply metalaxyl immediately. Destroy infected plants.",
    "Tomato - Leaf Mold": "Improve ventilation. Apply copper-based fungicide.",
    "Tomato - Septoria Leaf Spot": "Apply fungicide with chlorothalonil. Remove lower infected leaves.",
    "Tomato - Spider Mites": "Apply acaricide or neem oil. Increase humidity around plants.",
    "Tomato - Target Spot": "Apply azoxystrobin fungicide. Avoid wetting leaves when watering.",
    "Tomato - Yellow Leaf Curl Virus": "No cure. Remove infected plants. Control whitefly population.",
    "Tomato - Mosaic Virus": "No cure. Remove infected plants. Disinfect tools.",
    "Tomato - Healthy": "No treatment needed. Crop is healthy.",
}

session = ort.InferenceSession("cropdoc_v2_single.onnx")

def preprocess(image: Image.Image):
    image = image.resize((224, 224))
    img_array = np.array(image).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std
    img_array = img_array.transpose(2, 0, 1)
    img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
    return img_array

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    input_tensor = preprocess(image)
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_tensor})
    probabilities = np.exp(outputs[0]) / np.sum(np.exp(outputs[0]))
    predicted_idx = int(np.argmax(probabilities))
    confidence = float(np.max(probabilities)) * 100
    disease = CLASS_NAMES[predicted_idx]
    treatment = TREATMENTS[disease]
    return {
        "disease": disease,
        "confidence": round(confidence, 2),
        "treatment": treatment,
        "severity": "High" if confidence > 90 else "Moderate" if confidence > 70 else "Low"
    }

# --- Gemini Chat Endpoint ---

class ChatMessage(BaseModel):
    role: str  # "user" or "ai"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise HTTPException(status_code=500, detail="Gemini API Key not configured. Please set GEMINI_API_KEY in .env file.")

    model = genai.GenerativeModel('gemini-1.5-flash')

    # Build Gemini conversation history
    gemini_history = []

    # System context
    gemini_history.append({
        "role": "user",
        "parts": ["You are CropDoc, an expert AI agricultural advisor. You help farmers diagnose crop diseases, recommend treatments, find pesticides, and give practical farming advice. Be helpful, empathetic, and practical. Keep responses concise but thorough. If a farmer shares diagnosis results with you, reference those results in your advice."]
    })
    gemini_history.append({
        "role": "model",
        "parts": ["I understand. I am CropDoc, ready to help farmers with crop disease diagnosis and treatment advice. I'll be practical and empathetic in my responses."]
    })

    # Map conversation history (exclude the last user msg since send_message adds it)
    history_to_map = request.history[:-1] if len(request.history) > 0 else []
    for msg in history_to_map:
        role = "model" if msg.role == "ai" else "user"
        gemini_history.append({
            "role": role,
            "parts": [msg.content]
        })

    chat = model.start_chat(history=gemini_history)

    try:
        response = chat.send_message(request.message)
        return {"reply": response.text}
    except Exception as e:
        print(f"Gemini Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI chat error: {str(e)}")