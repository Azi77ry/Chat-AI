from flask import Flask, request, jsonify, render_template, g
from chatbot import DeepInfraChatBot
import speech_recognition as sr
import os
import time
import sqlite3
from pathlib import Path

app = Flask(__name__)
bot = DeepInfraChatBot()

# Configure speech recognition
recognizer = sr.Recognizer()
recognizer.energy_threshold = 4000
recognizer.dynamic_energy_threshold = True

# Database configuration
DATABASE = 'visitors.db'

def init_db():
    """Initialize database with simple counter"""
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visitor_count (
                id INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0
            )
        ''')
        # Initialize counter if not exists
        if conn.execute("SELECT 1 FROM visitor_count").fetchone() is None:
            conn.execute("INSERT INTO visitor_count (count) VALUES (0)")
            conn.commit()

def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        init_db()
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def increment_counter():
    """Increment visitor counter"""
    db = get_db()
    db.execute("UPDATE visitor_count SET count = count + 1")
    db.commit()
    return db.execute("SELECT count FROM visitor_count").fetchone()[0]

def get_count():
    """Get current visitor count"""
    db = get_db()
    return db.execute("SELECT count FROM visitor_count").fetchone()[0]

# System prompt configuration
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. Follow these guidelines:
1. Provide concise responses (1-3 sentences)
2. Be polite and professional
3. Clearly state when you don't know something
4. Never provide harmful, unethical, or dangerous information"""

bot._add_system_message(DEFAULT_SYSTEM_PROMPT)

@app.route('/')
def index():
    """Serve the chat interface with visitor count"""
    visitor_count = increment_counter()
    return render_template('index.html', visitor_count=visitor_count)

@app.route('/api/visitors', methods=['GET'])
def get_visitors():
    """API endpoint to get current visitor count"""
    return jsonify({"count": get_count()})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """Process text chat messages"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Invalid request format"}), 400
        
    user_input = data['message'].strip()
    if not user_input:
        return jsonify({"error": "Message cannot be empty"}), 400
        
    try:
        response = bot.chat(user_input)
        return jsonify({
            "response": response,
            "model": bot.model.split('/')[-1],
            "timestamp": int(time.time())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice', methods=['POST'])
def handle_voice():
    """Process voice messages"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
        
    audio_file = request.files['audio']
    temp_path = f"temp_audio_{int(time.time())}.wav"
    
    try:
        audio_file.save(temp_path)
        
        with sr.AudioFile(temp_path) as source:
            audio = recognizer.record(source)
            user_input = recognizer.recognize_google(audio)
            
        response = bot.chat(user_input)
        
        return jsonify({
            "user_input": user_input,
            "response": response,
            "model": bot.model.split('/')[-1],
            "timestamp": int(time.time())
        })
        
    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio"}), 400
    except sr.RequestError as e:
        return jsonify({"error": f"Speech recognition service error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/api/models', methods=['GET'])
def list_models():
    """Get available models"""
    return jsonify({
        "current": bot.model.split('/')[-1],
        "available": list(bot.SUPPORTED_MODELS.keys())
    })

@app.route('/api/model', methods=['POST'])
def switch_model():
    """Change the active model"""
    data = request.get_json()
    if not data or 'model' not in data:
        return jsonify({"error": "Model not specified"}), 400
        
    success = bot.set_model(data['model'])
    if success:
        return jsonify({
            "success": True,
            "new_model": bot.model.split('/')[-1]
        })
    return jsonify({"error": "Invalid model specified"}), 400

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    """Reset conversation history"""
    bot.clear_history()
    return jsonify({"success": True})

@app.before_request
def check_favicon():
    if request.path == '/favicon.ico':
        app.logger.info("Favicon requested")

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)