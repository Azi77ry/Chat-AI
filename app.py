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
recognizer.energy_threshold = 4000  # Adjust based on your microphone
recognizer.dynamic_energy_threshold = True

# Database setup
DATABASE = 'visitors.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Create table if it doesn't exist
        db.execute('''CREATE TABLE IF NOT EXISTS visitors
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def count_visitor():
    """Record a new visitor and return total count"""
    db = get_db()
    # Insert new visitor
    db.execute("INSERT INTO visitors DEFAULT VALUES")
    db.commit()
    # Get total count
    count = db.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    return count

# System prompt configuration
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. Follow these guidelines:
1. Provide concise responses (1-3 sentences)
2. Be polite and professional
3. Clearly state when you don't know something
4. Never provide harmful, unethical, or dangerous information"""

bot._add_system_message(DEFAULT_SYSTEM_PROMPT)

@app.route('/')
def index():
    """Serve the chat interface"""
    visitor_count = count_visitor()
    return render_template('index.html', visitor_count=visitor_count)

@app.route('/api/visitors', methods=['GET'])
def get_visitors():
    """Get current visitor count"""
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    return jsonify({"count": count})

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
        # Save and process audio
        audio_file.save(temp_path)
        
        with sr.AudioFile(temp_path) as source:
            audio = recognizer.record(source)
            user_input = recognizer.recognize_google(audio)
            
        # Get chatbot response
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
    # Ensure database exists
    Path(DATABASE).touch()
    app.run(host='0.0.0.0', port=5000, debug=True)