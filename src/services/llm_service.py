"""LLM service for generating responses using Google Gemini API."""

from typing import Optional
from config.settings import get_settings


class LLMService:
    """Service for interacting with Google Gemini API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            if self.settings.google_api_key:
                genai.configure(api_key=self.settings.google_api_key)
                # Use the default model
                self.client = genai
                print(f"Initialized Google Gemini API")
            else:
                print("Google API key not configured. Using fallback responses.")
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
            self.client = None
    
    def generate_response(
        self,
        query: str,
        context: str,
        chat_history: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response using the LLM."""
        
        # If API is available, use it
        if self.client is not None:
            return self._generate_with_api(query, context, chat_history, system_prompt)
        
        # Fallback: Generate response from context
        return self._generate_from_context(query, context)
    
    def _generate_with_api(
        self,
        query: str,
        context: str,
        chat_history: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate response using Google Gemini API."""
        try:
            # Build system prompt
            if system_prompt is None:
                system_prompt = self._get_default_system_prompt()
            
            # Build conversation history for context
            history_text = ""
            for msg in chat_history[-4:]:  # Keep last 4 messages
                role = "Student" if msg.get("role") == "user" else "Tutor"
                history_text += f"{role}: {msg.get('content', '')}\n\n"
            
            # Build the full prompt
            full_prompt = f"""{system_prompt}

TEXTBOOK CONTENT:
{context}

CONVERSATION HISTORY:
{history_text}

STUDENT QUESTION: {query}

Please provide a clear, step-by-step explanation suitable for a Grade 7 student. Use examples from the textbook when possible."""
            
            # Call Gemini using the default model
            model = self.client.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Error generating response with Gemini: {e}")
            return self._generate_from_context(query, context)
    
    def _generate_from_context(self, query: str, context: str) -> str:
        """Generate response directly from context without LLM."""
        if not context or context == "No relevant textbook content found for this question.":
            return f"I don't have specific information about '{query}' in the textbook. Could you try asking about a different topic or rephrasing your question?"
        
        # Extract key information from context
        lines = context.split('\n')
        relevant_lines = [line for line in lines if line.strip() and len(line.strip()) > 10]
        
        response = f"Based on the textbook material:\n\n"
        
        # Add first few relevant lines
        for line in relevant_lines[:5]:
            if line.strip():
                response += f"• {line.strip()}\n"
        
        response += f"\n\nWould you like me to explain any of these points in more detail?"
        
        return response
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for the tutor."""
        return """You are a neuro-inclusive science tutor for autistic students. Your role is to:

1. Use simple, clear language
2. Explain concepts step-by-step
3. Provide concrete examples from the textbook
4. Avoid unnecessary abstraction
5. Be patient and encouraging
6. Break down complex ideas into smaller parts
7. Use the provided textbook content as your primary source

Always ground your answers in the provided textbook material. If information is not in the textbook, say so clearly.
Keep responses concise but thorough."""
    
    def generate_follow_up_suggestions(self, response: str) -> list[str]:
        """Generate suggested follow-up questions."""
        if self.client is None:
            return [
                "Can you explain that differently?",
                "Give me an example",
                "What's the most important part?",
            ]
        
        try:
            prompt = f"""Based on this response, suggest 3 follow-up questions a student might ask:

Response: {response}

Return ONLY a JSON array of 3 strings, nothing else. Example: ["Question 1?", "Question 2?", "Question 3?"]"""
            
            model = self.client.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            import json
            # Extract JSON from response
            text = response.text.strip()
            # Find JSON array in response
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                suggestions = json.loads(json_str)
                return suggestions[:3]
            else:
                return [
                    "Can you explain that differently?",
                    "Give me an example",
                    "What's the most important part?",
                ]
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return [
                "Can you explain that differently?",
                "Give me an example",
                "What's the most important part?",
            ]
