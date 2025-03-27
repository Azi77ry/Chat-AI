from chatbot import AIChatBot
from voice_interface import VoiceInterface
import sys

class CLIInterface:
    def __init__(self):
        self.chatbot = AIChatBot()
        self.voice = VoiceInterface()
        self.running = False
        
    def start(self):
        """Start the command line interface"""
        self.running = True
        self._print_welcome()
        
        # Initial system message to guide the AI
        self.chatbot.add_system_message(
            "You are a helpful AI assistant. Be friendly, concise, and helpful. "
            "Provide clear answers and ask follow-up questions when appropriate."
        )
        
        while self.running:
            self._main_loop()
            
    def _print_welcome(self):
        print("\n" + "="*50)
        print("AI CHATBOT".center(50))
        print("="*50)
        print("\nChoose input method:")
        print("1. Type 't' for text input")
        print("2. Press Enter for voice input")
        print("3. Type 'quit' to exit")
        print("4. Type 'clear' to reset conversation")
        print("="*50 + "\n")
        
    def _main_loop(self):
        try:
            choice = input("\nChoose input method [t/Enter/quit/clear]: ").strip().lower()
            
            if choice == 'quit':
                self.running = False
                print("Goodbye!")
                return
            elif choice == 'clear':
                self.chatbot.clear_history()
                print("Conversation history cleared.")
                return
                
            user_input = None
            
            if choice == 't':
                user_input = input("You (text): ").strip()
            else:
                user_input = self.voice.listen()
                
            if not user_input:
                return
                
            if user_input.lower() in ['quit', 'exit']:
                self.running = False
                print("Goodbye!")
                return
                
            # Get AI response
            response = self.chatbot.chat(user_input)
            
            # Speak the response
            self.voice.speak(response)
            
        except KeyboardInterrupt:
            self.running = False
            print("\nGoodbye!")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    interface = CLIInterface()
    interface.start()