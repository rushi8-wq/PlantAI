import os
import io
import json
import secrets
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, stream_with_context, send_file
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from PIL import Image
import tensorflow as tf
from groq import Groq
from dotenv import load_dotenv

# Import the enhanced report generator
from report_generator import generate_enhanced_report

load_dotenv()

# Configure Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
MODEL_PATH = os.path.join(BASE_DIR, 'mobilenetv2_best.keras')
CLASS_NAMES_PATH = os.path.join(BASE_DIR, 'class_names.json')
IMG_SIZE = (224, 224)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Load model and class names globally
model = None
class_names = []

def load_model_and_classes():
    global model, class_names
    try:
        model = load_model(MODEL_PATH)
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None

    try:
        with open(CLASS_NAMES_PATH, 'r') as f:
            class_names = json.load(f)
        print(f"Loaded {len(class_names)} class names")
    except Exception as e:
        print(f"Error loading class names: {e}")

# ─── THE DYNAMIC DISSECTOR (Handles Millions of Leaves) ─────────────────────
def parse_class_name(raw_class):
    """Dissects names to infer biological categories at runtime."""
    parts = raw_class.split('___')
    plant = parts[0].replace('_', ' ').replace(',', '')
    condition = parts[1].replace('_', ' ') if len(parts) > 1 else 'Unknown'
    
    cond_lower = condition.lower()
    if "healthy" in cond_lower:
        category = "Healthy Tissue"
        is_healthy = True
    elif "bacterial" in cond_lower or "spot" in cond_lower:
        category = "Bacterial Pathogen"
        is_healthy = False
    elif "virus" in cond_lower or "mosaic" in cond_lower:
        category = "Viral Pathogen"
        is_healthy = False
    elif "rust" in cond_lower or "blight" in cond_lower or "scab" in cond_lower:
        category = "Fungal Pathogen"
        is_healthy = False
    else:
        category = "General Pathogen"
        is_healthy = False
        
    return plant, condition, category, is_healthy

# ─── THE PREDICTION ENGINE (Unpacks 4 values) ───────────────────────────────
def predict_image(filepath):
    if model is None:
        raise ValueError("Model not loaded")

    with Image.open(filepath) as img:
        img_rgb = img.convert('RGB')
        img_resized = img_rgb.resize(IMG_SIZE)
        img_array = np.array(img_resized)
    
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array.astype(np.float32))
    
    predictions = model.predict(img_array, verbose=0)
    predicted_idx = int(np.argmax(predictions[0]))
    confidence = float(np.max(predictions[0])) * 100

    raw_class = class_names[predicted_idx] if predicted_idx < len(class_names) else "Unknown"
    
    # Correctly unpacking 4 values to prevent errors
    plant_type, condition, pathogen_category, is_healthy = parse_class_name(raw_class)

    recommendations = []
    if is_healthy:
        severity_stage = "N/A"
        clinical_note = "Tissue shows no signs of active pathogen colonization."
        recommendations = [
            "Continue regular watering and care",
            "Monitor for any changes in appearance",
            "Maintain good air circulation"
        ]
    else:
        if confidence < 70:
            severity_stage = "Stage 1: Incubation / Early Detection"
            clinical_note = "Minimal necrotic tissue. Pathogen is in early colonization phase."
        elif 70 <= confidence < 90:
            severity_stage = "Stage 2: Active Lesion Progression"
            clinical_note = "Significant pathogen activity. Lesions are expanding."
        else:
            severity_stage = "Stage 3/4: Advanced Necrosis"
            clinical_note = "Critical tissue damage. High risk of secondary spread."
        
        recommendations = [
            "Isolate affected plants immediately",
            f"Apply appropriate {pathogen_category} treatment",
            "Sanitize all tools used on this plant",
            "Remove and safely dispose of heavily infected leaves"
        ]

    return {
        'raw_class': raw_class,
        'plant_type': plant_type,
        'condition': condition,
        'pathogen_category': pathogen_category,
        'severity_stage': severity_stage,
        'clinical_note': clinical_note,
        'is_healthy': is_healthy,
        'confidence': round(confidence, 2),
        'recommendations': recommendations
    }

# ─── AI Helper ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are PlantCare AI Assistant, an expert plant pathologist and agricultural advisor. 
Help users manage plant diseases based on the provided diagnosis context."""

def build_plant_context(prediction: dict) -> str:
    return (
        f"Plant: {prediction['plant_type']}\n"
        f"Condition: {prediction['condition']}\n"
        f"Pathogen: {prediction['pathogen_category']}\n"
        f"Stage: {prediction['severity_stage']}\n"
        f"Status: {'Healthy' if prediction['is_healthy'] else 'Disease Detected'}\n"
        f"Model Confidence: {prediction['confidence']}%"
    )

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def home(): return render_template('home.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/upload')
def upload(): return render_template('upload.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file:
        filename = secrets.token_hex(8) + os.path.splitext(file.filename)[1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            prediction = predict_image(filepath)
            static_filename = f"upload_{secrets.token_hex(8)}.jpg"
            static_path = os.path.join(app.config['STATIC_FOLDER'], static_filename)
            with Image.open(filepath) as img:
                img.convert('RGB').save(static_path)
            session['prediction'] = prediction
            session['image_path'] = f'images/{static_filename}'
            os.remove(filepath)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/result')
def result():
    prediction = session.get('prediction')
    image_path = session.get('image_path')
    if not prediction: return redirect(url_for('upload'))
    return render_template('result.html', prediction=prediction, image_path=image_path)

@app.route('/report')
def report():
    prediction = session.get('prediction')
    if not prediction: return redirect(url_for('upload'))
    
    # Ask AI for data - specifically requesting strings
    scientific_query = (
    f"As a Senior Plant Pathologist, provide a research-grade JSON for {prediction['plant_type']} infected with {prediction['condition']}. "
    f"Include: 'pathogen_name' (Latin name), 'taxonomy' (list of Rank:Name strings), "
    f"'mechanism' (2-3 sentences on how it infects), 'organic_protocol' (specific dosages), "
    f"'chemical_protocol' (specific fungicides and dosages), 'spread_pattern' (how it travels)."
)
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": scientific_query}],
            response_format={ "type": "json_object" }
        )
        sci_data = json.loads(response.choices[0].message.content)

        # CRITICAL FIX: Ensure lists are converted to strings to prevent the .split() error
        for key in ['organic_protocol', 'chemical_protocol', 'mechanism', 'spread_pattern']:
            val = sci_data.get(key, "N/A")
            if isinstance(val, list):
                sci_data[key] = "<br/>".join(val)
            elif val is None:
                sci_data[key] = "N/A"
    except Exception as e:
        print(f"AI Fetch Error: {e}")
        sci_data = {"pathogen_name": "N/A", "taxonomy": [], "organic_protocol": "N/A", "chemical_protocol": "N/A"}

    full_image_path = os.path.join(BASE_DIR, 'static', session.get('image_path'))
    
    pdf_bytes = generate_enhanced_report(
        prediction=prediction,
        sci_data=sci_data,
        image_path=full_image_path
    )
    
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, 
                     download_name=f"Scientific_Report_{prediction['plant_type']}.pdf")
# ─── AI CHATBOT LOGIC ────────────────────────────────────────────────────────

@app.route('/learn', methods=['POST'])
def learn():
    prediction = session.get('prediction')
    if not prediction: return jsonify({'error': 'No prediction'}), 400
    
    panel = request.json.get('panel', 'overview')
    plant_context = build_plant_context(prediction)
    
    prompts = {
        'overview': f"Diagnosis:\n{plant_context}\nProvide a detailed biological overview and pathogen cause.",
        'prevention': f"Diagnosis:\n{plant_context}\nProvide cultural, organic, and chemical prevention steps.",
        'damage': f"Diagnosis:\n{plant_context}\nProvide short and long-term risk assessment and yield impact."
    }
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": prompts.get(panel, prompts['overview'])}]
        )
        return jsonify({'content': response.choices[0].message.content, 'panel': panel})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    prediction = session.get('prediction')
    if not prediction: return jsonify({'error': 'No prediction'}), 400
    
    messages = request.json.get('messages', [])
    context_system = f"{SYSTEM_PROMPT}\n\nContext:\n{build_plant_context(prediction)}"
    groq_messages = [{"role": "system", "content": context_system}] + messages

    def generate():
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            stream=True
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text: yield f"data: {text.replace('\n', '\\n')}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

load_model_and_classes()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)