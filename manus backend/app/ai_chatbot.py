try:
    import google.generativeai as genai
except Exception:
    genai = None
import requests
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

# If genai isn't available we can fall back to calling the Generative Language REST API
# directly using the provided API key. We'll keep USE_GEMINI_REST True if we at least have
# an API key and requests is available; later code will choose genai client first if
# present, otherwise REST.
USE_GEMINI_REST = False
if GEMINI_API_KEY and genai is None:
    USE_GEMINI_REST = True

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
    # Provider selection: SDK-first (try multiple SDK call shapes) -> REST Gemini -> Groq -> Fallback
    system_instruction = (
        "You are a sophisticated, helpful, and knowledgeable customer support assistant for a premium, luxury e-commerce marketplace. "
        "Your tone is polite, professional, and elegant. "
        "Your primary goal is to assist with product inquiries, order status, and general site navigation in a concise manner. "
        "Always maintain the luxury brand voice. "
        "If you are asked a question outside the scope of e-commerce or customer support, politely decline and redirect the user to a relevant shopping topic."
    )

    # 1) Try SDK if available (be tolerant of different SDK shapes/versions)
    if genai is not None and GEMINI_API_KEY:
        try:
            # If SDK exposes a configure helper, call it safely
            if hasattr(genai, "configure"):
                try:
                    genai.configure(api_key=GEMINI_API_KEY)
                except Exception:
                    # not critical; some SDKs accept the key per-call
                    pass

            # Variant A: genai.chat.completions.create (newer chat-style APIs)
            chat_api = getattr(genai, "chat", None)
            if chat_api is not None and hasattr(chat_api, "completions") and hasattr(chat_api.completions, "create"):
                try:
                    messages = [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_query},
                    ]
                    resp = genai.chat.completions.create(model="gemini-1.5", messages=messages, temperature=0.3)
                    # resp may contain different shapes
                    text = None
                    if hasattr(resp, "output_text"):
                        text = resp.output_text
                    elif isinstance(resp, dict):
                        # common dict shape
                        choices = resp.get("choices") or resp.get("candidates")
                        if choices and isinstance(choices, list):
                            first = choices[0]
                            if isinstance(first, dict):
                                text = first.get("message") or first.get("content") or first.get("output") or first.get("text")
                    if text:
                        return text
                except Exception:
                    pass

            # Variant B: genai.models.generate (text-generation style)
            models_api = getattr(genai, "models", None)
            if models_api is not None and hasattr(models_api, "generate"):
                try:
                    prompt = system_instruction + "\n\n" + user_query
                    resp = genai.models.generate(model="gemini-1.5", prompt=[{"type":"text","text":prompt}], temperature=0.3, max_output_tokens=512)
                    # extract text
                    if isinstance(resp, dict):
                        # candidates / output
                        candidates = resp.get("candidates") or resp.get("outputs") or []
                        if candidates and isinstance(candidates, list):
                            first = candidates[0]
                            text = first.get("content") or first.get("output") or first.get("text") if isinstance(first, dict) else None
                            if text:
                                return text
                except Exception:
                    pass

            # Variant C: older pattern (GenerativeModel with start_chat)
            if hasattr(genai, "GenerativeModel"):
                try:
                    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_instruction)
                    chat = model.start_chat(history=[])
                    response = chat.send_message(user_query, request_options={"timeout": 15})
                    if hasattr(response, "text"):
                        return response.text
                except Exception:
                    pass
        except Exception as e:
            # Fall through to REST/Groq/fallback
            print(f"Gemini SDK attempt failed: {e}")

    # If genai client not available, try REST endpoint
    if USE_GEMINI_REST and GEMINI_API_KEY:
        try:
            # Build a simple prompt that includes a system instruction and recent conversation
            system_instruction = (
                "You are a sophisticated, helpful, and knowledgeable customer support assistant for a premium, luxury e-commerce marketplace. "
                "Your tone is polite, professional, and elegant. "
                "Your primary goal is to assist with product inquiries, order status, and general site navigation in a concise manner. "
                "Always maintain the luxury brand voice. "
                "If you are asked a question outside the scope of e-commerce or customer support, politely decline and redirect the user to a relevant shopping topic."
            )

            # Maintain rolling history per session (system + last N messages)
            history_msgs = CHAT_SESSIONS.get(session_id, {}).get("messages", [])
            # Ensure system at start
            if not history_msgs or history_msgs[0].get("role") != "system":
                history_msgs = [{"role": "system", "content": system_instruction}]

            # Append user message
            history_msgs.append({"role": "user", "content": user_query})

            # Keep length reasonable
            if len(history_msgs) > 15:
                history_msgs = [history_msgs[0]] + history_msgs[-14:]

            CHAT_SESSIONS[session_id] = {"provider": "gemini_rest", "messages": history_msgs}

            # Flatten messages into a single prompt for generateText
            prompt_parts = [str(m.get("content")) for m in history_msgs if m.get("content")]
            prompt = "\n\n".join(prompt_parts)

            # Choose a model name; this may be adjusted depending on availability
            model = "gemini-1.5"
            url = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generateText?key={GEMINI_API_KEY}"

            payload = {
                "prompt": {"text": prompt},
                "temperature": 0.3,
                "maxOutputTokens": 512,
            }

            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Attempt to extract text from common response shapes
            text = None
            if isinstance(data, dict):
                candidates = data.get("candidates") or data.get("outputs") or []
                if candidates and isinstance(candidates, list):
                    first = candidates[0]
                    text = first.get("content") or first.get("output") or first.get("text") or first.get("message")
                if not text:
                    text = data.get("output") or data.get("response") or None
                    if isinstance(text, dict):
                        text = text.get("content") or text.get("text")

            if not text:
                return get_fallback_response(user_query)

            # Append assistant response to session history
            CHAT_SESSIONS[session_id]["messages"].append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            print(f"Error calling Gemini REST API, falling back: {e}")
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


