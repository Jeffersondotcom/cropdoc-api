from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
import gdown

MODEL_PATH = "cropdoc_v2_single_v2.onnx"

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
    "Apple - Apple Scab",                          # 0
    "Apple - Black Rot",                           # 1
    "Apple - Cedar Apple Rust",                    # 2
    "Apple - Healthy",                             # 3
    "Blueberry - Healthy",                         # 4
    "Cherry - Powdery Mildew",                     # 5
    "Cherry - Healthy",                            # 6
    "Corn - Cercospora Leaf Spot",                 # 7
    "Corn - Common Rust",                          # 8
    "Corn - Northern Leaf Blight",                 # 9
    "Corn - Healthy",                              # 10
    "Grape - Black Rot",                           # 11
    "Grape - Esca (Black Measles)",                # 12
    "Grape - Leaf Blight",                         # 13
    "Grape - Healthy",                             # 14
    "Orange - Citrus Greening",                    # 15
    "Peach - Bacterial Spot",                      # 16
    "Peach - Healthy",                             # 17
    "Pepper - Bacterial Spot",                     # 18
    "Pepper - Healthy",                            # 19
    "Potato - Early Blight",                       # 20
    "Potato - Late Blight",                        # 21
    "Potato - Healthy",                            # 22
    "Raspberry - Healthy",                         # 23
    "Soybean - Healthy",                           # 24
    "Squash - Powdery Mildew",                     # 25
    "Strawberry - Leaf Scorch",                    # 26
    "Strawberry - Healthy",                        # 27
    "Tomato - Bacterial Spot",                     # 28
    "Tomato - Early Blight",                       # 29
    "Tomato - Late Blight",                        # 30
    "Tomato - Leaf Mold",                          # 31
    "Tomato - Septoria Leaf Spot",                 # 32
    "Tomato - Spider Mites",                       # 33
    "Tomato - Target Spot",                        # 34
    "Tomato - Yellow Leaf Curl Virus",             # 35
    "Tomato - Mosaic Virus",                       # 36
    "Tomato - Healthy",                            # 37
]

TREATMENTS = {
    "Apple - Apple Scab": "Apply fungicide with myclobutanil. Remove infected leaves.",
"Apple - Black Rot": "Prune infected branches. Apply captan-based fungicide.",
"Apple - Cedar Apple Rust": "Apply fungicide at bud break. Remove nearby juniper hosts.",
"Apple - Healthy": "No treatment needed.",
"Blueberry - Healthy": "No treatment needed.",
"Cherry - Powdery Mildew": "Apply sulfur-based fungicide. Improve air circulation.",
"Cherry - Healthy": "No treatment needed.",
"Grape - Black Rot": "Apply mancozeb fungicide. Remove mummified fruit.",
"Grape - Esca (Black Measles)": "No cure. Remove infected wood. Apply wound sealant.",
"Grape - Leaf Blight": "Apply copper-based fungicide. Remove infected leaves.",
"Grape - Healthy": "No treatment needed.",
"Orange - Citrus Greening": "No cure. Remove infected trees. Control psyllid population.",
"Peach - Bacterial Spot": "Apply copper bactericide. Avoid overhead irrigation.",
"Peach - Healthy": "No treatment needed.",
"Raspberry - Healthy": "No treatment needed.",
"Soybean - Healthy": "No treatment needed.",
"Squash - Powdery Mildew": "Apply potassium bicarbonate or neem oil spray.",
"Strawberry - Leaf Scorch": "Apply fungicide. Remove infected leaves. Avoid overhead watering.",
"Strawberry - Healthy": "No treatment needed.",
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
    return {"status": "GreenDoc API is running"}

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

    if confidence < 50:
        return {
            "disease": "Not a crop leaf",
            "confidence": round(confidence, 2),
            "treatment": "Please photograph a crop leaf in natural lighting. Point your camera at an affected leaf, not fruit, stem, or soil.",
            "severity": "None",
            "warning": "Image does not appear to be a crop leaf."
        }

    return {
    "disease": disease if confidence >= 85 else "Uncertain",
    "confidence": round(confidence, 2),
    "treatment": treatment if confidence >= 85 else "Confidence too low for a reliable diagnosis. Please take a clearer photo of the affected leaf in good lighting.",
    "severity": "High" if confidence > 90 else "Moderate" if confidence > 70 else "Low",
    "warning": None if confidence >= 85 else "Low confidence prediction. Results may not be accurate."
}