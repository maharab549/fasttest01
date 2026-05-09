import requests

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

NVIDIA_API_KEY = settings.nvidia_api_key
USE_NVIDIA = bool(NVIDIA_API_KEY)


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
    """Provides a simple rule-based fallback response when NVIDIA is unavailable.

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
    """Generates a response to a user query using NVIDIA's chat completion API, maintaining conversation history.
    Falls back to rule-based responses if NVIDIA is unavailable.
    
    Args:
        user_query: The user's message.
        session_id: A unique ID to identify the user's chat session.
        
    Returns:
        The chatbot's response.
    """
    # Hard scope guard: chatbot is website/app-domain only.
    if not is_megamart_related_query(user_query):
        return get_off_topic_response()

    # Provider selection: NVIDIA API -> fallback
    system_instruction = build_megamart_system_instruction()

    try:
        history_msgs = CHAT_SESSIONS.get(session_id, {}).get("messages", [])
        if not history_msgs or history_msgs[0].get("role") != "system":
            history_msgs = [{"role": "system", "content": system_instruction}]

        history_msgs.append({"role": "user", "content": user_query})

        if len(history_msgs) > 13:
            history_msgs = [history_msgs[0]] + history_msgs[-12:]

        CHAT_SESSIONS[session_id] = {"provider": "nvidia", "messages": history_msgs}

        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta/llama-4-maverick-17b-128e-instruct",
                "messages": history_msgs,
                "max_tokens": 512,
                "temperature": 0.6,
                "top_p": 1.00,
                "frequency_penalty": 0.00,
                "presence_penalty": 0.00,
                "stream": False,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text = None
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            text = msg.get("content") if isinstance(msg, dict) else None
        if not text:
            return get_fallback_response(user_query)

        CHAT_SESSIONS[session_id]["messages"].append({"role": "assistant", "content": text})
        return text
    except Exception as e:
        print(f"Error with NVIDIA API, falling back: {e}")
        if session_id in CHAT_SESSIONS:
            del CHAT_SESSIONS[session_id]
        return get_fallback_response(user_query)

