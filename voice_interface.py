import pyttsx3
import speech_recognition as sr
import time
from typing import Optional

class VoiceInterface:
    def __init__(self):
        """Initialize voice recognition and synthesis"""
        self.engine = self._init_tts()
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8  # seconds of silence to end speech
        self.recognizer.energy_threshold = 300  # minimum audio energy to consider for recording
        
    def _init_tts(self):
        """Initialize text-to-speech engine"""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)  # Use first available voice
        engine.setProperty('rate', 150)  # Speed of speech
        return engine
        
    def speak(self, text: str):
        """Convert text to speech and play it"""
        print(f"AI: {text}")  # Also print to console
        self.engine.say(text)
        self.engine.runAndWait()
        
    def listen(self) -> Optional[str]:
        """Listen to microphone input and convert to text"""
        with sr.Microphone() as source:
            print("\nListening... (say 'stop' to end voice input)")
            try:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"You said: {text}")
                    return text
                except sr.UnknownValueError:
                    print("Sorry, I didn't understand that.")
                    return None
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
                    return None
                    
            except sr.WaitTimeoutError:
                print("Listening timed out. Please try again.")
                return None
            except Exception as e:
                print(f"Error during listening: {str(e)}")
                return None