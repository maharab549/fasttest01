try:
    import google.generativeai as genai
except Exception:
    genai = None
try:
    from groq import Groq
except Exception:
    Groq = None

from app.config import settings
from typing import Dict, Any
import re

# Dictionary to store chat sessions (user_id -> chat_session)
# Since FastAPI is stateless, this is a simplified in-memory store.
# In a production environment, this would be a Redis or database store.
CHAT_SESSIONS: Dict[str, Any] = {}

# Initialize providers (API keys loaded from settings)
GEMINI_API_KEY = settings.gemini_api_key
GROQ_API_KEY = settings.groq_api_key
USE_GEMINI = False  # Flags to track availability
USE_GROQ = False

if GEMINI_API_KEY and genai is not None:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_GEMINI = True
    except Exception as e:
        print(f"Failed to configure Gemini API: {e}")
        USE_GEMINI = False

# Configure Groq if available
GROQ_CLIENT = None
if GROQ_API_KEY and Groq is not None:
    try:
        GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)
        USE_GROQ = True
    except Exception as e:
        print(f"Failed to configure Groq API: {e}")
        USE_GROQ = False


def get_fallback_response(user_query: str) -> str:
    """Provides a simple rule-based fallback response when Gemini is unavailable."""
    query_lower = user_query.lower()
    
    # Greeting patterns
    if re.search(r'\b(hi|hello|hey|greetings)\b', query_lower):
        return "Hello! Welcome to our premium marketplace. How may I assist you today? You can ask me about products, orders, shipping, or any other shopping-related questions."
    
    # Product inquiry patterns
    if re.search(r'\b(product|item|buy|purchase|shop|looking for)\b', query_lower):
        return "I'd be happy to help you find products! You can browse our categories, use the search bar, or filter products by price, rating, and more. What type of product are you interested in?"
    
    # Order/shipping patterns
    if re.search(r'\b(order|shipping|delivery|track|status)\b', query_lower):
        return "For order-related inquiries, please visit your Orders page where you can track your shipments and view order details. If you need specific help, please provide your order number."
    
    # Payment patterns
    if re.search(r'\b(payment|pay|card|checkout|stripe)\b', query_lower):
        return "We accept secure payments through Stripe, supporting all major credit cards. Your payment information is encrypted and safe. Is there anything specific about the payment process you'd like to know?"
    
    # Return/refund patterns
    if re.search(r'\b(return|refund|exchange|cancel)\b', query_lower):
        return "Our return policy allows you to return items within 30 days of delivery. Please visit your Orders page to initiate a return. For specific questions, feel free to contact our customer support."
    
    # Account patterns
    if re.search(r'\b(account|profile|login|register|sign)\b', query_lower):
        return "You can manage your account from the Account page. There you can update your profile, view order history, manage addresses, and adjust preferences. Need help with something specific?"
    
    # Help/support patterns
    if re.search(r'\b(help|support|assist|question|problem|issue)\b', query_lower):
        return "I'm here to help! I can assist with product searches, order tracking, account management, and general shopping questions. What would you like help with?"
    
    # Gratitude patterns
    if re.search(r'\b(thank|thanks|appreciate)\b', query_lower):
        return "You're very welcome! If you have any other questions, I'm always here to help. Enjoy your shopping experience!"
    
    # Default response
    return "Thank you for your message. I'm here to assist with product inquiries, order tracking, account management, and shopping questions. How can I help you today?"

def get_chatbot_response(user_query: str, session_id: str = "default_user") -> str:
    """Generates a response to a user query using Google Gemini API, maintaining conversation history.
    Falls back to rule-based responses if Gemini is unavailable.
    
    Args:
        user_query: The user's message.
        session_id: A unique ID to identify the user's chat session.
        
    Returns:
        The chatbot's response.
    """
    # Provider selection: Gemini -> Groq -> Fallback
    if USE_GEMINI and GEMINI_API_KEY and genai is not None:
        try:
            # 1. Define the system instruction for a luxury e-commerce assistant
            system_instruction = (
                "You are a sophisticated, helpful, and knowledgeable customer support assistant for a premium, luxury e-commerce marketplace. "
                "Your tone is polite, professional, and elegant. "
                "Your primary goal is to assist with product inquiries, order status, and general site navigation in a concise manner. "
                "Always maintain the luxury brand voice. "
                "If you are asked a question outside the scope of e-commerce or customer support, politely decline and redirect the user to a relevant shopping topic."
            )

            # 2. Get or create a chat session for the user
            if session_id not in CHAT_SESSIONS:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction
                )
                chat = model.start_chat(history=[])
                CHAT_SESSIONS[session_id] = {"provider": "gemini", "chat": chat}
            else:
                # If previous provider differs, reset to Gemini
                if CHAT_SESSIONS[session_id].get("provider") != "gemini":
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=system_instruction
                    )
                    chat = model.start_chat(history=[])
                    CHAT_SESSIONS[session_id] = {"provider": "gemini", "chat": chat}
                else:
                    chat = CHAT_SESSIONS[session_id]["chat"]

            response = chat.send_message(
                user_query,
                request_options={"timeout": 15}
            )
            return response.text
        except Exception as e:
            print(f"Error with Gemini API, trying Groq fallback: {e}")
            # Clean up to avoid corrupted session
            if session_id in CHAT_SESSIONS:
                del CHAT_SESSIONS[session_id]

    if USE_GROQ and GROQ_CLIENT is not None:
        try:
            # Prepare a small rolling chat history for better context
            system_message = {
                "role": "system",
                "content": (
                    "You are a refined, concise assistant for a premium e-commerce marketplace. "
                    "Help users with product discovery, order status, returns, and payments. "
                    "Maintain a polite, premium brand tone."
                )
            }

            if session_id not in CHAT_SESSIONS or CHAT_SESSIONS[session_id].get("provider") != "groq":
                CHAT_SESSIONS[session_id] = {"provider": "groq", "messages": [system_message]}

            messages = CHAT_SESSIONS[session_id]["messages"]
            messages.append({"role": "user", "content": user_query})

            # Keep only the last ~6 turns to stay concise
            if len(messages) > 13:
                # keep system + last 12
                messages = [messages[0]] + messages[-12:]
                CHAT_SESSIONS[session_id]["messages"] = messages

            # Call Groq chat completion
            resp = GROQ_CLIENT.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=messages,
                temperature=0.6,
                max_tokens=512,
                top_p=1,
            )
            text = resp.choices[0].message.content if resp.choices else ""
            if not text:
                return get_fallback_response(user_query)

            messages.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            print(f"Error with Groq API, falling back to rule-based responses: {e}")
            if session_id in CHAT_SESSIONS:
                del CHAT_SESSIONS[session_id]
            return get_fallback_response(user_query)

    # Final fallback
    return get_fallback_response(user_query)


