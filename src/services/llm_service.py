"""LLM service for generating responses using Google Gemini API."""

from typing import Optional
from config.settings import get_settings
from src.services.api_key_manager import get_api_key_manager


class LLMService:
    """Service for interacting with Google Gemini API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.api_key_manager = get_api_key_manager()
        self._init_client()
    
    def _init_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            # API key is already configured by the key manager
            self.client = genai
            print(f"Initialized Google Gemini API with rotating keys")
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
        """Generate response using Google Gemini API with key rotation."""
        try:
            # Check if any API keys are available
            manager_status = self.api_key_manager.get_status()
            all_limited = all(not key['is_available'] for key in manager_status['keys'])
            
            if all_limited:
                print("⚠️ All API keys are rate-limited. Using fallback response.")
                return self._generate_from_context_formatted(query, context)
            
            # Build system prompt
            if system_prompt is None:
                system_prompt = self._get_default_system_prompt()
            
            # Build conversation history for context
            history_text = ""
            for msg in chat_history[-4:]:  # Keep last 4 messages
                role = "Student" if msg.get("role") == "user" else "Tutor"
                history_text += f"{role}: {msg.get('content', '')}\n\n"
            
            # Build the full prompt - ask for ONE section only
            full_prompt = f"""{system_prompt}

TEXTBOOK CONTENT:
{context}

CONVERSATION HISTORY:
{history_text}

STUDENT QUESTION: {query}

IMPORTANT INSTRUCTIONS:
1. Explain ONLY ONE main concept or section
2. Use the textbook content provided above as your primary source
3. Include concrete examples from the textbook
4. Use simple language suitable for a Grade 7 student
5. Use bullet points for lists
6. Explain WHY things work, not just WHAT they are
7. Keep the explanation focused and not too long (2-3 paragraphs max)
8. After explaining this one concept, STOP and wait for the student to confirm they understand
9. Do NOT provide multiple sections or a summary - just ONE section

FORMAT YOUR RESPONSE AS:
**[Section Title]**
[Detailed explanation with examples from textbook]

• [Key point 1]
• [Key point 2]
• [Key point 3]

(Then STOP - do not add more sections)"""
            
            # Call Gemini using the default model with generation config
            generation_config = {
                'max_output_tokens': 2048,  # Allow longer responses
                'temperature': 0.7,
            }
            model = self.client.GenerativeModel(
                'gemini-2.5-flash',
                generation_config=generation_config
            )
            response = model.generate_content(full_prompt)
            
            # Record successful request
            self.api_key_manager.record_request()
            
            return response.text
        except Exception as e:
            error_str = str(e)
            print(f"Error generating response with Gemini: {e}")
            print(f"Error type: {type(e).__name__}")
            
            # Check if it's a rate limit error
            if "quota" in error_str.lower() or "rate" in error_str.lower() or "429" in error_str:
                print("⚠ Rate limit detected, rotating to next API key...")
                self.api_key_manager.mark_rate_limited()
                # Try again with the new key
                try:
                    generation_config = {
                        'max_output_tokens': 2048,
                        'temperature': 0.7,
                    }
                    model = self.client.GenerativeModel(
                        'gemini-2.5-flash',
                        generation_config=generation_config
                    )
                    response = model.generate_content(full_prompt)
                    self.api_key_manager.record_request()
                    return response.text
                except Exception as retry_error:
                    print(f"Retry failed: {retry_error}")
                    return self._generate_from_context_formatted(query, context)
            
            # Use fallback with better formatting
            return self._generate_from_context_formatted(query, context)
    
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
    
    def _generate_from_context_formatted(self, query: str, context: str) -> str:
        """Generate formatted response directly from context (for when API is unavailable)."""
        if not context or context == "No relevant textbook content found for this question.":
            return f"I don't have specific information about '{query}' in the textbook. Could you try asking about a different topic or rephrasing your question?"
        
        # Clean up the context - remove "From [chapter]:" prefixes and extra formatting
        cleaned_context = context.replace('From ', '').replace(':\n', '\n')
        
        # Split into sentences and clean up
        sentences = []
        for line in cleaned_context.split('\n'):
            line = line.strip()
            if line and len(line) > 20:
                # Remove special characters and clean up
                line = line.replace('\uf06e', '').replace('Key Points:', '').strip()
                # Split on periods to get individual sentences
                if line and not line.startswith('•'):
                    # Handle sentences that end with periods
                    parts = line.split('. ')
                    for part in parts:
                        part = part.strip()
                        if part and len(part) > 20:
                            # Add period back if it was removed
                            if not part.endswith('.'):
                                part += '.'
                            sentences.append(part)
        
        if not sentences:
            return "I found some information in the textbook, but I'm having trouble processing it right now. Please try again in a moment."
        
        # Build a coherent response with proper formatting
        response = "**From the Textbook:**\n\n"
        
        # Add main content - each sentence on its own line for better readability
        for i, sentence in enumerate(sentences[:4]):
            response += f"{sentence}\n\n"
        
        # Add key points if available
        if len(sentences) > 4:
            response += "**Key Points:**\n\n"
            for sentence in sentences[4:7]:
                # Format as bullet points
                response += f"• {sentence}\n\n"
        
        response += "*Note: This is a simplified view from the textbook. For a more detailed explanation, please try again later.*"
        
        return response
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for the tutor."""
        return """You are a neuro-inclusive science tutor for autistic students. Your role is to:

1. Use simple, clear language
2. Explain ONE concept or section at a time
3. Provide concrete examples from the textbook
4. Avoid unnecessary abstraction
5. Be patient and encouraging
6. Break down complex ideas into smaller parts
7. Use the provided textbook content as your primary source
8. IMPORTANT: Explain only ONE section/subsection per response, then STOP and wait for user confirmation

Always ground your answers in the provided textbook material. If information is not in the textbook, say so clearly.
Keep responses focused on a single concept - not too long, not too short."""
    
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
            
            generation_config = {
                'max_output_tokens': 512,  # Shorter for suggestions
                'temperature': 0.7,
            }
            model = self.client.GenerativeModel(
                'gemini-2.5-flash',
                generation_config=generation_config
            )
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
