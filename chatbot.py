import os
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class DeepInfraChatBot:
    def __init__(self, model: str = "meta-llama/Meta-Llama-3-8B-Instruct", max_history: int = 6):
        """
        Initialize the chatbot with DeepInfra backend
        
        Args:
            model: DeepInfra model identifier
            max_history: Maximum conversation history to retain
        """
        self.client = OpenAI(
            base_url="https://api.deepinfra.com/v1/openai",
            api_key=os.getenv("DEEPINFRA_API_KEY")
        )
        self.model = model
        self.max_history = max_history
        self.conversation_history: List[Dict] = []
        
        # Supported models with their API names
        self.SUPPORTED_MODELS = {
            "llama3-70b": "meta-llama/Meta-Llama-3-70B-Instruct",
            "llama3-8b": "meta-llama/Meta-Llama-3-8B-Instruct",
            "mixtral": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "mistral": "mistralai/Mistral-7B-Instruct-v0.1"
        }
        
        # Initialize with default system message
        self._add_system_message("You are a helpful AI assistant.")

    def _add_system_message(self, content: str):
        """Add or update the system message"""
        # Remove any existing system messages
        self.conversation_history = [
            msg for msg in self.conversation_history 
            if msg["role"] != "system"
        ]
        # Add new system message at beginning
        self.conversation_history.insert(0, {"role": "system", "content": content})
        
    def _trim_history(self):
        """Maintain conversation history within limits"""
        if len(self.conversation_history) > self.max_history:
            # Keep system message and most recent messages
            system_msg = next(
                (msg for msg in self.conversation_history if msg["role"] == "system"), 
                None
            )
            other_msgs = self.conversation_history[-self.max_history + (1 if system_msg else 0):]
            self.conversation_history = ([system_msg] if system_msg else []) + other_msgs
    
    def set_model(self, model_key: str) -> bool:
        """Switch to a different model"""
        if model_key in self.SUPPORTED_MODELS:
            self.model = self.SUPPORTED_MODELS[model_key]
            return True
        return False
    
    def chat(self, user_input: str) -> str:
        """
        Process user input and return AI response
        
        Args:
            user_input: The user's message text
            
        Returns:
            The AI's response text
        """
        if not user_input.strip():
            return "Please enter a valid message."
            
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Get AI response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=350,
                timeout=10  # seconds
            )
            
            ai_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            self._trim_history()
            
            return ai_response
            
        except Exception as e:
            error_msg = str(e)
            
            # Model-specific fallbacks
            if "70B" in self.model and "timeout" in error_msg.lower():
                self.set_model("llama3-8b")
                return "Switched to faster model. Please try again."
                
            return f"Error: {error_msg}"

    def clear_history(self, keep_system: bool = True):
        """Reset conversation history"""
        if keep_system:
            self.conversation_history = [
                msg for msg in self.conversation_history 
                if msg["role"] == "system"
            ]
        else:
            self.conversation_history = []