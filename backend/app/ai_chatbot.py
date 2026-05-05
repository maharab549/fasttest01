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

MEGAMART_SCOPE_KEYWORDS = {
    "megamart", "marketplace", "product", "products", "category", "categories", "catalog",
    "search", "cart", "checkout", "order", "orders", "track", "tracking", "delivery",
    "shipping", "return", "returns", "refund", "exchange", "cancel", "payment", "payments",
    "promo", "coupon", "discount", "deal", "deals", "flash sale", "new arrivals", "top rated",
    "wishlist", "favorite", "favorites", "review", "reviews", "rating", "profile", "account",
    "address", "address book", "notification", "notifications", "message", "messages",
    "support", "help", "faq", "seller", "admin", "dashboard", "rewards", "loyalty",
    "sms", "chatbot", "ai assistant", "contact", "privacy", "terms", "policy"
}

OFF_TOPIC_RESPONSE = (
    "I can only help with MegaMart website and app topics. "
    "Please ask about products, orders, delivery, payments, returns, account, seller/admin features, or support pages."
)

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


def is_megamart_related_query(user_query: str) -> bool:
    text = (user_query or "").strip().lower()
    if not text:
        return True

    # Allow simple greetings so users can start naturally.
    if re.search(r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b", text):
        return True

    if "megamart" in text or "mega mart" in text:
        return True

    for kw in MEGAMART_SCOPE_KEYWORDS:
        if kw in text:
            return True

    return False


def build_megamart_system_instruction() -> str:
    return (
        "You are MegaMart Assistant, the official support chatbot for the MegaMart website and APK only. "
        "Your scope is strictly limited to MegaMart platform topics.\n\n"
        "MegaMart platform knowledge:\n"
        "- Customer features: home feed, search, categories, product details, cart, checkout, orders, order tracking, returns, rewards/loyalty, favorites, notifications, messages, and profile/account settings.\n"
        "- Deals surfaces: All Deals, Flash Sale (countdown), New Arrivals, and Top Rated.\n"
        "- Support and info pages: Help/FAQ, Contact Us, Privacy Policy, Terms & Conditions.\n"
        "- Payments: card checkout and integrated payment flows available in app/backend.\n"
        "- Multi-role platform: customer, seller dashboard/tools, and admin dashboard/tools.\n\n"
        "Behavior rules:\n"
        "1) Answer only MegaMart-related questions.\n"
        "2) If a question is unrelated to MegaMart, politely refuse and redirect to MegaMart topics.\n"
        "3) Do not invent unavailable data. If account-specific data is requested, guide the user to the relevant app page or ask for needed order/product identifiers.\n"
        "4) Keep responses concise, practical, and support-focused.\n"
        "5) Maintain a professional, friendly customer-support tone."
    )


def get_off_topic_response() -> str:
    return OFF_TOPIC_RESPONSE


def get_fallback_response(user_query: str) -> str:
    """Provides a simple rule-based fallback response when Gemini is unavailable.

    This version also appends a small set of follow-up suggestions (intent-aware)
    to help guide the user to common next steps.
    """
    if not is_megamart_related_query(user_query):
        return get_off_topic_response()

    query_lower = user_query.lower()

    intent = "default"
    resp = None

    # Greeting patterns
    if re.search(r'\b(hi|hello|hey|greetings)\b', query_lower):
        intent = "greeting"
        resp = (
            "Hello! Welcome to MegaMart. How can I help you today? "
            "You can ask about products, orders, shipping, returns, payments, or account settings."
        )

    # Product inquiry patterns
    elif re.search(r'\b(product|item|buy|purchase|shop|looking for)\b', query_lower):
        intent = "product"
        resp = (
            "I can help you find products on MegaMart. You can browse categories, use search, "
            "or filter by price, rating, and deals. What product are you looking for?"
        )

    # Order/shipping patterns
    elif re.search(r'\b(order|shipping|delivery|track|status)\b', query_lower):
        intent = "order"
        resp = (
            "For order inquiries, please open your Orders page in MegaMart where you can track shipment and view order details. "
            "If you need specific help, please provide your order number."
        )

    # Payment patterns
    elif re.search(r'\b(payment|pay|card|checkout|stripe)\b', query_lower):
        intent = "payment"
        resp = (
            "MegaMart supports secure in-app payment methods. Your payment information is encrypted and safe. "
            "Is there anything specific about the payment process you'd like to know?"
        )

    # Return/refund patterns
    elif re.search(r'\b(return|refund|exchange|cancel)\b', query_lower):
        intent = "return"
        resp = (
            "Please use your Orders page in MegaMart to start a return or refund request. "
            "For specific questions, feel free to contact our customer support."
        )

    # Account patterns
    elif re.search(r'\b(account|profile|login|register|sign)\b', query_lower):
        intent = "account"
        resp = (
            "You can manage your account from the Account/Profile area. There you can update your profile, view order history, manage addresses, "
            "and adjust preferences. Need help with something specific?"
        )

    # Help/support patterns
    elif re.search(r'\b(help|support|assist|question|problem|issue)\b', query_lower):
        intent = "support"
        resp = (
            "I'm here to help with MegaMart topics. I can assist with product search, order tracking, account management, and support pages. "
            "What would you like help with?"
        )

    # Gratitude patterns
    elif re.search(r'\b(thank|thanks|appreciate)\b', query_lower):
        intent = "gratitude"
        resp = "You're very welcome! If you have any other questions, I'm always here to help. Enjoy your shopping experience!"

    # Default response
    if resp is None:
        intent = "default"
        resp = (
            "Thanks for your message. I can assist with MegaMart product inquiries, orders, returns, payments, account settings, and support pages. "
            "How can I help you today?"
        )

    # Append intent-aware follow-up suggestions
    suggestions = get_followup_suggestions(intent)
    return f"{resp}\n\n{suggestions}"


def get_followup_suggestions(intent: str) -> str:
    """Return a short, user-friendly string of follow-up suggestions based on detected intent."""
    common = {
        "greeting": [
            "Browse new arrivals",
            "Search for a product (e.g. 'red dress')",
            "View my orders"
        ],
        "product": [
            "Show me similar products",
            "Filter by price or rating",
            "Do you have this in a different size or color?"
        ],
        "order": [
            "Track my order (provide order number)",
            "Where is my delivery?",
            "Initiate a return"
        ],
        "payment": [
            "Help with payment methods",
            "Apply a promo code",
            "Is my payment secure?"
        ],
        "return": [
            "Start a return for an order",
            "Check refund status",
            "Contact support about returns"
        ],
        "account": [
            "Update my shipping address",
            "Change my password",
            "View order history"
        ],
        "support": [
            "Contact customer support",
            "Open a support ticket",
            "Report a problem with an order"
        ],
        "gratitude": [
            "You're welcome — anything else?",
            "Search for products",
            "View your account"
        ],
        "default": [
            "Search for products (e.g. 'leather boots')",
            "Track an order (provide order number)",
            "Ask about returns or refunds"
        ]
    }

    picks = common.get(intent, common["default"])
    # Format as a short sentence with examples separated by " • " for compactness
    return "You can try: " + " • ".join(picks)

def get_chatbot_response(user_query: str, session_id: str = "default_user") -> str:
    """Generates a response to a user query using Google Gemini API, maintaining conversation history.
    Falls back to rule-based responses if Gemini is unavailable.
    
    Args:
        user_query: The user's message.
        session_id: A unique ID to identify the user's chat session.
        
    Returns:
        The chatbot's response.
    """
    # Hard scope guard: chatbot is website/app-domain only.
    if not is_megamart_related_query(user_query):
        return get_off_topic_response()

    # Provider selection: SDK-first (try multiple SDK call shapes) -> REST Gemini -> Groq -> Fallback
    system_instruction = build_megamart_system_instruction()

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
            system_instruction = build_megamart_system_instruction()

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
                "content": build_megamart_system_instruction()
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

