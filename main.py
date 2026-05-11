from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
import gdown

MODEL_PATH = "cropdoc_v2_single.onnx"

if not os.path.exists(MODEL_PATH):
    print("Downloading v2 model from Google Drive...")
    gdown.download(
        "https://drive.google.com/uc?id=1XglOrkbrtAn0G6DT60y3k_RT_blVUR3d",
        MODEL_PATH,
        quiet=False
    )
    print("Model downloaded.")

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

session = ort.InferenceSession(MODEL_PATH)

def preprocess(image: Image.Image):
    image = image.resize((224, 224))
    img_array = np.array(image).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std
    img_array = img_array.transpose(2, 0, 1)
    img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
    return img_array

@app.get("/")
def root():
    return {"status": "CropDoc API is running"}

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
    "disease": disease if confidence >= 70 else "Uncertain",
    "confidence": round(confidence, 2),
    "treatment": treatment if confidence >= 70 else "Confidence too low for a reliable diagnosis. Please take a clearer photo of the affected leaf in good lighting.",
    "severity": "High" if confidence > 90 else "Moderate" if confidence > 70 else "Low",
    "warning": None if confidence >= 70 else "Low confidence prediction. Results may not be accurate."
}