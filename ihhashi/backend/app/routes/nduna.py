"""
Nduna Chatbot - Multilingual AI Assistant for iHhashi
Supports all 6 South African languages with Groq LLM
Now with Product Browsing and Voice Input!
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import os
import json
from datetime import datetime
from bson import ObjectId

from app.database import get_collection

router = APIRouter(prefix="/nduna", tags=["nduna"])

# Groq API keys (rotation for load balancing) - loaded from environment
def get_groq_api_keys():
    """Load Groq API keys from environment"""
    keys = []
    for i in range(1, 20):
        key = os.getenv(f"GROQ_API_KEY_{i}")
        if key:
            keys.append(key)
    return keys if keys else ["fallback-key"]

GROQ_API_KEYS = get_groq_api_keys()

# Additional API keys - loaded from environment
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

def get_google_keys():
    """Load Google API keys from environment"""
    keys = []
    for i in range(1, 10):
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key:
            keys.append(key)
    return keys

GOOGLE_KEYS = get_google_keys()

# Key rotation for rate limiting
current_key_index = 0


def get_next_groq_key():
    """Rotate through Groq API keys for load balancing"""
    global current_key_index
    key = GROQ_API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
    return key


# Language configurations
LANGUAGES = {
    "en": {
        "name": "English",
        "greeting": "Hello! I'm Nduna, your iHhashi assistant. How can I help you today?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa. 
You help customers with:
- Placing and tracking orders
- Finding stores, restaurants, and products
- Delivery questions
- Account and payment help
- General support

You have access to functions to search for merchants and products. When users ask about food, groceries, or products, use the search_merchants and search_products functions to provide real results.

Be friendly, concise, and helpful. Use South African context when appropriate.
Respond in English unless the user speaks another language."""
    },
    "zu": {
        "name": "isiZulu",
        "greeting": "Sawubona! NginguNduna, umsizi wakho we-iHhashi. Ngingakusiza kanjani namuhla?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in isiZulu (Zulu) language.
Use South African context and cultural references when appropriate."""
    },
    "xh": {
        "name": "isiXhosa",
        "greeting": "Molo! NdinguNduna, umncedi wakho we-iHhashi. Ndingakunceda njani namhlanje?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in isiXhosa (Xhosa) language.
Use South African context and cultural references when appropriate."""
    },
    "af": {
        "name": "Afrikaans",
        "greeting": "Hallo! Ek is Nduna, jou iHhashi-assistent. Hoe kan ek jou vandag help?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in Afrikaans language.
Use South African context and cultural references when appropriate."""
    },
    "st": {
        "name": "Sesotho",
        "greeting": "Dumela! Ke Nduna, motho ya thusang ho iHhashi. Nka u thusa joang kajeno?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in Sesotho (Sotho) language.
Use South African context and cultural references when appropriate."""
    },
    "tn": {
        "name": "Setswana",
        "greeting": "Dumela! Ke Nduna, motho yo o thusang mo iHhashi. Nka go thusa jang gompieno?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in Setswana (Tswana) language.
Use South African context and cultural references when appropriate."""
    },
    "so": {
        "name": "Sesotho sa Leboa (Northern Sotho)",
        "greeting": "Thobela! Ke Nduna, motho wa thuso wa iHhashi. Nka go thuša bjang lehono?",
        "system_prompt": """You are Nduna, a friendly and helpful AI assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, finding stores and products, delivery, and support.
You have access to functions to search for merchants and products.
Be friendly, concise, and helpful. Respond in Sesotho sa Leboa (Northern Sotho/Pedi) language.
Use South African context and cultural references when appropriate."""
    }
}

# Function definitions for Groq function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_merchants",
            "description": "Search for stores, restaurants, or merchants on iHhashi. Use when user asks about food, groceries, pharmacies, or nearby places to order from.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'pizza', 'grocery', 'pharmacy')"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["grocery", "pharmacy", "restaurant", "retail", "convenience"],
                        "description": "Category filter"
                    },
                    "city": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for specific products or menu items. Use when user asks about specific dishes, items, or products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product name or description"
                    },
                    "merchant_id": {
                        "type": "string",
                        "description": "Optional merchant ID to search within a specific store"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_menu",
            "description": "Get the full menu or product catalog for a specific merchant/store. Use after search_merchants when user wants to see what a store offers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {
                        "type": "string",
                        "description": "The merchant/store ID"
                    }
                },
                "required": ["merchant_id"]
            }
        }
    }
]


class ChatMessage(BaseModel):
    message: str
    language: str = "en"
    user_id: Optional[str] = None
    context: Optional[dict] = None
    conversation_history: Optional[List[dict]] = []


class ChatResponse(BaseModel):
    response: str
    language: str
    suggestions: Optional[List[str]] = None


class LanguageInfo(BaseModel):
    code: str
    name: str
    greeting: str


class VoiceTranscriptionResponse(BaseModel):
    text: str
    language: str
    duration_seconds: Optional[float] = None


class BrowseResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str


# ============ FUNCTION IMPLEMENTATIONS ============

async def search_merchants_impl(query: str, category: str = None, city: str = None, lat: float = None, lng: float = None) -> Dict:
    """Search merchants in database"""
    stores_col = get_collection("stores")
    
    search_query = {"status": "active"}
    
    if category:
        search_query["category"] = category
    
    if city:
        search_query["city"] = {"$regex": city, "$options": "i"}
    
    if query:
        search_query["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    
    cursor = stores_col.find(search_query).limit(10)
    stores = await cursor.to_list(length=10)
    
    results = []
    for store in stores:
        results.append({
            "id": str(store["_id"]),
            "name": store.get("name"),
            "category": store.get("category"),
            "description": store.get("description", ""),
            "city": store.get("address", {}).get("city", ""),
            "rating": store.get("rating", 4.5),
            "is_open": store.get("is_open", True)
        })
    
    return {"merchants": results, "total": len(results)}


async def search_products_impl(query: str, merchant_id: str = None) -> Dict:
    """Search products in database"""
    products_col = get_collection("products")
    
    search_query = {"is_available": True}
    
    if merchant_id:
        search_query["store_id"] = merchant_id
    
    if query:
        search_query["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    
    cursor = products_col.find(search_query).limit(20)
    products = await cursor.to_list(length=20)
    
    results = []
    for product in products:
        results.append({
            "id": str(product["_id"]),
            "name": product.get("name"),
            "price": product.get("price"),
            "category": product.get("category"),
            "description": product.get("description", ""),
            "store_id": product.get("store_id")
        })
    
    return {"products": results, "total": len(results)}


async def get_merchant_menu_impl(merchant_id: str) -> Dict:
    """Get merchant's menu/product catalog"""
    products_col = get_collection("products")
    
    query = {"store_id": merchant_id, "is_available": True}
    cursor = products_col.find(query).sort("category", 1)
    products = await cursor.to_list(length=100)
    
    categorized = {}
    for product in products:
        category = product.get("category", "Other")
        if category not in categorized:
            categorized[category] = []
        categorized[category].append({
            "id": str(product["_id"]),
            "name": product.get("name"),
            "price": product.get("price"),
            "description": product.get("description", "")
        })
    
    return {"menu": categorized, "categories": list(categorized.keys())}


# Function handler for Groq tool calls
async def handle_tool_call(tool_name: str, arguments: dict) -> Any:
    """Execute function calls from Groq"""
    if tool_name == "search_merchants":
        return await search_merchants_impl(
            query=arguments.get("query", ""),
            category=arguments.get("category"),
            city=arguments.get("city")
        )
    elif tool_name == "search_products":
        return await search_products_impl(
            query=arguments.get("query", ""),
            merchant_id=arguments.get("merchant_id")
        )
    elif tool_name == "get_merchant_menu":
        return await get_merchant_menu_impl(
            merchant_id=arguments.get("merchant_id")
        )
    return {"error": f"Unknown function: {tool_name}"}


# ============ ENDPOINTS ============

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    languages = [
        LanguageInfo(code=code, name=lang["name"], greeting=lang["greeting"])
        for code, lang in LANGUAGES.items()
    ]
    return {"languages": languages}


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """
    Chat with Nduna AI assistant with function calling support
    
    Now supports browsing merchants and products!
    """
    lang_code = chat_message.language.lower()
    if lang_code not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang_code}")
    
    language_config = LANGUAGES[lang_code]
    
    # Build conversation for Groq with tools
    messages = [
        {"role": "system", "content": language_config["system_prompt"]}
    ]
    
    if chat_message.conversation_history:
        for msg in chat_message.conversation_history[-10:]:
            messages.append(msg)
    
    messages.append({"role": "user", "content": chat_message.message})
    
    if chat_message.context:
        context_str = f"\n\nCurrent context:\n"
        if chat_message.context.get("order_status"):
            context_str += f"Order status: {chat_message.context['order_status']}\n"
        if chat_message.context.get("location"):
            context_str += f"Location: {chat_message.context['location']}\n"
        messages[0]["content"] += context_str
    
    api_key = get_next_groq_key()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # First call with tools
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "max_tokens": 800,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 429:
                api_key = get_next_groq_key()
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "tools": TOOLS,
                        "tool_choice": "auto",
                        "max_tokens": 800,
                        "temperature": 0.7
                    }
                )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Groq API error")
            
            data = response.json()
            assistant_message = data["choices"][0]["message"]
            
            # Handle tool calls if present
            if assistant_message.get("tool_calls"):
                messages.append(assistant_message)
                
                for tool_call in assistant_message["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    # Execute the function
                    function_result = await handle_tool_call(function_name, arguments)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(function_result)
                    })
                
                # Get final response after tool calls
                api_key = get_next_groq_key()
                final_response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "max_tokens": 800,
                        "temperature": 0.7
                    }
                )
                
                if final_response.status_code == 200:
                    data = final_response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                else:
                    ai_response = "I found some results but couldn't format them. Please try again."
            else:
                ai_response = assistant_message.get("content", "I'm here to help!")
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    suggestions = generate_suggestions(chat_message.message, chat_message.context)
    
    return ChatResponse(
        response=ai_response,
        language=lang_code,
        suggestions=suggestions
    )


# ============ NEW VOICE ENDPOINT ============

@router.post("/voice", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    audio_file: UploadFile = File(...),
    language: str = Form(default="en")
):
    """
    Transcribe voice message using Groq Whisper
    
    Accepts audio files (mp3, mp4, mpeg, mpga, m4a, wav, webm)
    Returns transcribed text
    """
    # Supported formats
    supported_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    file_ext = audio_file.filename.split(".")[-1].lower() if audio_file.filename else ""
    
    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported: {', '.join(supported_formats)}"
        )
    
    # Read audio file
    audio_content = await audio_file.read()
    
    api_key = get_next_groq_key()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Create multipart form for Whisper API
            files = {
                "file": (audio_file.filename or "audio.mp3", audio_content, audio_file.content_type or "audio/mpeg")
            }
            
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data={
                    "model": "whisper-large-v3-turbo",
                    "language": language if language != "auto" else None,
                    "response_format": "json"
                }
            )
            
            if response.status_code == 429:
                # Retry with next key
                api_key = get_next_groq_key()
                files = {
                    "file": (audio_file.filename or "audio.mp3", audio_content, audio_file.content_type or "audio/mpeg")
                }
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                    data={
                        "model": "whisper-large-v3-turbo",
                        "response_format": "json"
                    }
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Whisper API error: {response.text}"
                )
            
            data = response.json()
            transcribed_text = data.get("text", "")
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Transcription timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return VoiceTranscriptionResponse(
        text=transcribed_text,
        language=language,
        duration_seconds=None
    )


@router.post("/voice/chat", response_model=ChatResponse)
async def voice_chat(
    audio_file: UploadFile = File(...),
    language: str = Form(default="en"),
    user_id: Optional[str] = Form(default=None)
):
    """
    Voice-to-chat: Transcribe audio and get AI response in one call
    
    Perfect for Telegram voice messages!
    """
    # First transcribe
    transcription = await transcribe_voice(audio_file, language)
    
    # Then chat
    chat_message = ChatMessage(
        message=transcription.text,
        language=language,
        user_id=user_id
    )
    
    return await chat(chat_message)


# ============ BROWSE ENDPOINTS ============

@router.get("/browse/merchants", response_model=BrowseResponse)
async def browse_merchants(
    query: str = "",
    category: str = None,
    city: str = None,
    limit: int = 20
):
    """
    Browse merchants/stores directly
    
    Categories: grocery, pharmacy, restaurant, retail, convenience
    """
    result = await search_merchants_impl(query, category, city)
    
    return BrowseResponse(
        results=result["merchants"],
        total=result["total"],
        query=query
    )


@router.get("/browse/products", response_model=BrowseResponse)
async def browse_products(
    query: str = "",
    merchant_id: str = None,
    limit: int = 20
):
    """Browse products directly"""
    result = await search_products_impl(query, merchant_id)
    
    return BrowseResponse(
        results=result["products"],
        total=result["total"],
        query=query
    )


@router.get("/browse/{merchant_id}/menu")
async def browse_menu(merchant_id: str):
    """Get merchant's menu/catalog"""
    return await get_merchant_menu_impl(merchant_id)


def generate_suggestions(message: str, context: Optional[dict]) -> List[str]:
    """Generate quick reply suggestions based on message and context"""
    suggestions = []
    
    message_lower = message.lower()
    
    if "order" in message_lower:
        suggestions = [
            "Track my order",
            "Cancel order",
            "Contact rider",
            "Order again"
        ]
    elif "restaurant" in message_lower or "food" in message_lower:
        suggestions = [
            "Nearby restaurants",
            "Popular dishes",
            "Special offers",
            "My favorites"
        ]
    elif "store" in message_lower or "shop" in message_lower or "grocery" in message_lower:
        suggestions = [
            "Nearby stores",
            "Browse groceries",
            "Find pharmacies",
            "Special offers"
        ]
    elif "deliver" in message_lower:
        suggestions = [
            "Delivery status",
            "Delivery time",
            "Change address",
            "Contact support"
        ]
    elif "pay" in message_lower or "payment" in message_lower:
        suggestions = [
            "Payment methods",
            "Add card",
            "View receipts",
            "Refund status"
        ]
    else:
        suggestions = [
            "Find food nearby",
            "Browse stores",
            "Track order",
            "Get help"
        ]
    
    return suggestions[:4]


@router.post("/quick-replies")
async def get_quick_replies(context: dict):
    """Get context-aware quick reply suggestions"""
    suggestions = []
    
    if context.get("screen") == "home":
        suggestions = [
            {"text": "Order food", "action": "search"},
            {"text": "My orders", "action": "orders"},
            {"text": "Nearby deals", "action": "deals"}
        ]
    elif context.get("screen") == "order_tracking":
        suggestions = [
            {"text": "Contact rider", "action": "call_rider"},
            {"text": "Order details", "action": "order_details"},
            {"text": "Help", "action": "support"}
        ]
    elif context.get("screen") == "checkout":
        suggestions = [
            {"text": "Apply promo code", "action": "promo"},
            {"text": "Change delivery time", "action": "schedule"},
            {"text": "Add tip", "action": "tip"}
        ]
    
    return {"suggestions": suggestions}


@router.get("/greeting/{language}")
async def get_greeting(language: str):
    """Get greeting message for a specific language"""
    lang_code = language.lower()
    if lang_code not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang_code}")
    
    return {
        "language": lang_code,
        "greeting": LANGUAGES[lang_code]["greeting"],
        "language_name": LANGUAGES[lang_code]["name"]
    }
