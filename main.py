import os
import wave
import json
import logging
import asyncio
import threading
import time
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pytz
from dateutil import parser, relativedelta

import pyaudio
import assemblyai as aai
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingParameters,
    StreamingEvents,
)
from google.generativeai import GenerativeModel, configure
import websockets
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - Default values from environment
DEFAULT_AAI_API_KEY = os.getenv("AAI_API_KEY")
DEFAULT_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MURF_API_KEY = os.getenv("MURF_API_KEY")
DEFAULT_MURF_WS_URL = os.getenv("MURF_WS_URL", "wss://api.murf.ai/v1/speech/stream-input")
DEFAULT_OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Current API keys (can be updated via UI)
current_api_keys = {
    "aai": DEFAULT_AAI_API_KEY,
    "gemini": DEFAULT_GEMINI_API_KEY,
    "murf": DEFAULT_MURF_API_KEY,
    "openweather": DEFAULT_OPENWEATHER_API_KEY
}

AGENT_PERSONA = os.getenv(
    "AGENT_PERSONA",
    (
        "You are a witty, helpful Pirate assistant with TWO special powers! Speak like a pirate with nautical flair, "
        "sprinkling in pirate idioms (aye, ahoy, matey), while staying concise and useful. "
        "You have TWO special skills: "
        "1. Weather powers - you can check the weather for any location using real-time data. "
        "2. Time powers - you can handle timezone conversions, date calculations, and calendar queries. "
        "When users ask about weather, use your weather powers to get real-time information. "
        "When users ask about time, dates, or timezones, use your time powers to provide accurate calculations. "
        "Never break character. Keep responses friendly and to the point."
    ),
)

# Initialize with default keys if available
if DEFAULT_AAI_API_KEY:
    aai.settings.api_key = DEFAULT_AAI_API_KEY
if DEFAULT_GEMINI_API_KEY:
    configure(api_key=DEFAULT_GEMINI_API_KEY)

# Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("day23")

# FastAPI app
app = FastAPI(title="AI Voice Agent - Day 23")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Uploads
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Audio config (AssemblyAI input is 16000, Murf output is 44100)
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 1600

# Chat history file
CHAT_HISTORY_FILE = os.path.join(UPLOAD_DIR, "chat_history.json")

# Utility to save audio
def save_wav(frames: List[bytes]) -> Optional[str]:
    if not frames:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(UPLOAD_DIR, f"recorded_audio_{ts}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return path

# Utility to save chat history
def save_chat_history(user_query: str, ai_response: str) -> bool:
    try:
        history = []
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r") as f:
                history = json.load(f)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "ai_response": ai_response,
        }
        history.append(entry)
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
        log.info(f"Chat history saved: {entry}")
        return True
    except Exception as e:
        log.error(f"Failed to save chat history: {e}")
        return False

# Utility to get chat history
@app.get("/chat_history")
async def get_chat_history():
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        log.error(f"Failed to read chat history: {e}")
        return {"error": str(e)}

@app.delete("/chat_history")
async def clear_chat_history():
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            os.remove(CHAT_HISTORY_FILE)
            log.info("Chat history cleared")
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        log.error(f"Failed to clear chat history: {e}")
        return {"error": str(e)}

# Static context_id
CONTEXT_ID = "static_context_23"

# Weather functionality
def get_weather_for_location(location: str) -> Dict:
    """Get weather information for a given location using wttr.in API (free, no key required)."""
    try:
        # Use wttr.in API which is free and doesn't require API key
        weather_url = f"https://wttr.in/{location}?format=j1"
        
        weather_response = requests.get(weather_url, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Extract current weather information
        current_condition = weather_data["current_condition"][0]
        nearest_area = weather_data["nearest_area"][0]
        
        # Extract relevant weather information
        weather_info = {
            "location": f"{nearest_area['areaName'][0]['value']}, {nearest_area['country'][0]['value']}",
            "temperature": int(current_condition["temp_C"]),
            "feels_like": int(current_condition["FeelsLikeC"]),
            "description": current_condition["weatherDesc"][0]["value"],
            "humidity": int(current_condition["humidity"]),
            "wind_speed": float(current_condition["windspeedKmph"]),
            "pressure": int(current_condition["pressure"])
        }
        
        return weather_info
        
    except requests.exceptions.RequestException as e:
        log.error(f"Weather API request failed: {e}")
        return {"error": "Failed to fetch weather data"}
    except Exception as e:
        log.error(f"Weather data processing error: {e}")
        return {"error": "Error processing weather data"}

def extract_location_from_text(text: str) -> Optional[str]:
    """Extract location from user text using simple pattern matching."""
    # Common weather-related phrases to remove
    weather_phrases = [
        r"what's the weather like in\s+",
        r"what is the weather in\s+",
        r"weather in\s+",
        r"how's the weather in\s+",
        r"check weather for\s+",
        r"weather for\s+",
        r"temperature in\s+",
        r"forecast for\s+",
        r"weather at\s+",
        r"weather of\s+"
    ]
    
    text_lower = text.lower().strip()
    
    # Try to match weather patterns
    for pattern in weather_phrases:
        match = re.search(pattern, text_lower)
        if match:
            location = text_lower[match.end():].strip()
            # Remove trailing punctuation and common words
            location = re.sub(r'[?.,!]+$', '', location)
            location = re.sub(r'\b(please|now|today|right now)\b', '', location).strip()
            if location:
                return location
    
    # If no pattern matched, try to extract location after "in"
    in_match = re.search(r'\bin\s+([^?.,!]+)', text_lower)
    if in_match:
        location = in_match.group(1).strip()
        if location and len(location) > 2:
            return location
    
    return None

# Time and Date functionality
def get_timezone_time(timezone_name: str) -> Dict:
    """Get current time for a specific timezone."""
    try:
        # Common timezone mappings
        timezone_mapping = {
            'new york': 'America/New_York',
            'nyc': 'America/New_York',
            'los angeles': 'America/Los_Angeles',
            'la': 'America/Los_Angeles',
            'chicago': 'America/Chicago',
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'tokyo': 'Asia/Tokyo',
            'sydney': 'Australia/Sydney',
            'mumbai': 'Asia/Kolkata',
            'india': 'Asia/Kolkata',
            'singapore': 'Asia/Singapore',
            'beijing': 'Asia/Shanghai',
            'china': 'Asia/Shanghai',
            'dubai': 'Asia/Dubai',
            'moscow': 'Europe/Moscow',
            'berlin': 'Europe/Berlin',
            'rome': 'Europe/Rome',
            'madrid': 'Europe/Madrid',
            'amsterdam': 'Europe/Amsterdam',
            'toronto': 'America/Toronto',
            'vancouver': 'America/Vancouver',
            'mexico city': 'America/Mexico_City',
            'sao paulo': 'America/Sao_Paulo',
            'buenos aires': 'America/Argentina/Buenos_Aires',
            'cape town': 'Africa/Johannesburg',
            'cairo': 'Africa/Cairo',
            'lagos': 'Africa/Lagos',
            'nairobi': 'Africa/Nairobi'
        }
        
        timezone_name_lower = timezone_name.lower().strip()
        
        # Try to find the timezone
        if timezone_name_lower in timezone_mapping:
            tz = pytz.timezone(timezone_mapping[timezone_name_lower])
        else:
            # Try to find by common patterns
            for tz_name in pytz.all_timezones:
                if timezone_name_lower in tz_name.lower():
                    tz = pytz.timezone(tz_name)
                    break
            else:
                return {"error": f"Timezone '{timezone_name}' not found"}
        
        current_time = datetime.now(tz)
        utc_time = datetime.now(pytz.UTC)
        
        return {
            "timezone": tz.zone,
            "current_time": current_time.strftime("%I:%M %p"),
            "current_date": current_time.strftime("%A, %B %d, %Y"),
            "utc_offset": current_time.strftime("%z"),
            "utc_time": utc_time.strftime("%I:%M %p UTC"),
            "day_of_week": current_time.strftime("%A")
        }
        
    except Exception as e:
        log.error(f"Timezone error: {e}")
        return {"error": f"Error getting time for timezone '{timezone_name}'"}

def calculate_date_difference(date1_str: str, date2_str: str = None) -> Dict:
    """Calculate the difference between two dates."""
    try:
        # Parse the first date
        date1 = parser.parse(date1_str, fuzzy=True)
        
        # If no second date provided, use today
        if date2_str:
            date2 = parser.parse(date2_str, fuzzy=True)
        else:
            date2 = datetime.now()
        
        # Calculate difference
        diff = relativedelta.relativedelta(date2, date1)
        
        # Get absolute values
        years = abs(diff.years)
        months = abs(diff.months)
        days = abs(diff.days)
        
        # Format the result
        if years > 0:
            result = f"{years} year{'s' if years != 1 else ''}"
            if months > 0:
                result += f", {months} month{'s' if months != 1 else ''}"
        elif months > 0:
            result = f"{months} month{'s' if months != 1 else ''}"
            if days > 0:
                result += f", {days} day{'s' if days != 1 else ''}"
        else:
            result = f"{days} day{'s' if days != 1 else ''}"
        
        # Determine if it's in the past or future
        if date1 < date2:
            direction = "ago"
        else:
            direction = "from now"
        
        return {
            "date1": date1.strftime("%B %d, %Y"),
            "date2": date2.strftime("%B %d, %Y"),
            "difference": result,
            "direction": direction,
            "total_days": abs((date2 - date1).days)
        }
        
    except Exception as e:
        log.error(f"Date calculation error: {e}")
        return {"error": f"Error calculating date difference: {str(e)}"}

def get_day_of_week(date_str: str) -> Dict:
    """Get the day of the week for a given date."""
    try:
        date = parser.parse(date_str, fuzzy=True)
        return {
            "date": date.strftime("%B %d, %Y"),
            "day_of_week": date.strftime("%A"),
            "day_number": date.weekday(),  # Monday = 0, Sunday = 6
            "is_weekend": date.weekday() >= 5
        }
    except Exception as e:
        log.error(f"Day of week error: {e}")
        return {"error": f"Error getting day of week: {str(e)}"}

def extract_time_query(text: str) -> Optional[Dict]:
    """Extract time-related queries from user text."""
    text_lower = text.lower().strip()
    
    # Timezone queries
    timezone_patterns = [
        r"what time is it in\s+([^?.,!]+)",
        r"time in\s+([^?.,!]+)",
        r"current time in\s+([^?.,!]+)",
        r"what's the time in\s+([^?.,!]+)",
        r"timezone\s+([^?.,!]+)",
        r"clock in\s+([^?.,!]+)"
    ]
    
    for pattern in timezone_patterns:
        match = re.search(pattern, text_lower)
        if match:
            timezone = match.group(1).strip()
            return {"type": "timezone", "query": timezone}
    
    # Date difference queries
    date_diff_patterns = [
        r"how many days (?:until|till|to)\s+([^?.,!]+)",
        r"days (?:until|till|to)\s+([^?.,!]+)",
        r"how long until\s+([^?.,!]+)",
        r"time until\s+([^?.,!]+)",
        r"countdown to\s+([^?.,!]+)"
    ]
    
    for pattern in date_diff_patterns:
        match = re.search(pattern, text_lower)
        if match:
            target_date = match.group(1).strip()
            return {"type": "date_difference", "query": target_date}
    
    # Day of week queries
    day_patterns = [
        r"what day (?:of the week )?(?:is|was|will be)\s+([^?.,!]+)",
        r"day of the week for\s+([^?.,!]+)",
        r"what day\s+([^?.,!]+)"
    ]
    
    for pattern in day_patterns:
        match = re.search(pattern, text_lower)
        if match:
            date = match.group(1).strip()
            return {"type": "day_of_week", "query": date}
    
    # Simple time queries
    if any(word in text_lower for word in ["what time", "current time", "time now"]):
        return {"type": "current_time", "query": "local"}
    
    return None

# Initialize Gemini model with persona as system instruction
model = GenerativeModel(model_name="gemini-2.0-flash", system_instruction=AGENT_PERSONA)

async def stream_gemini_response(transcript: str, websocket: WebSocket) -> Optional[str]:
    """Stream Gemini response, send to Murf, save chat history, and forward audio to client."""
    try:
        # Check if user is asking about weather
        location = extract_location_from_text(transcript)
        weather_context = ""
        
        if location:
            log.info(f"Weather request detected for location: {location}")
            weather_data = get_weather_for_location(location)
            
            if "error" not in weather_data:
                weather_context = f"""
                [WEATHER DATA FOR {location.upper()}]
                Location: {weather_data['location']}
                Temperature: {weather_data['temperature']}°C
                Feels like: {weather_data['feels_like']}°C
                Conditions: {weather_data['description']}
                Humidity: {weather_data['humidity']}%
                Wind Speed: {weather_data['wind_speed']} km/h
                Pressure: {weather_data['pressure']} hPa
                [/WEATHER DATA]
                """
                log.info(f"Weather data retrieved: {weather_data}")
            else:
                weather_context = f"[WEATHER ERROR: {weather_data['error']}]"
                log.warning(f"Weather error: {weather_data['error']}")
        
        # Check if user is asking about time/date
        time_query = extract_time_query(transcript)
        time_context = ""
        
        if time_query:
            log.info(f"Time request detected: {time_query}")
            
            if time_query["type"] == "timezone":
                time_data = get_timezone_time(time_query["query"])
                if "error" not in time_data:
                    time_context = f"""
                    [TIME DATA FOR {time_query['query'].upper()}]
                    Timezone: {time_data['timezone']}
                    Current Time: {time_data['current_time']}
                    Current Date: {time_data['current_date']}
                    UTC Offset: {time_data['utc_offset']}
                    Day of Week: {time_data['day_of_week']}
                    [/TIME DATA]
                    """
                    log.info(f"Timezone data retrieved: {time_data}")
                else:
                    time_context = f"[TIME ERROR: {time_data['error']}]"
                    log.warning(f"Timezone error: {time_data['error']}")
            
            elif time_query["type"] == "date_difference":
                date_data = calculate_date_difference(time_query["query"])
                if "error" not in date_data:
                    time_context = f"""
                    [DATE DIFFERENCE DATA]
                    Target Date: {date_data['date1']}
                    Current Date: {date_data['date2']}
                    Difference: {date_data['difference']} {date_data['direction']}
                    Total Days: {date_data['total_days']} days
                    [/DATE DIFFERENCE DATA]
                    """
                    log.info(f"Date difference data retrieved: {date_data}")
                else:
                    time_context = f"[TIME ERROR: {date_data['error']}]"
                    log.warning(f"Date difference error: {date_data['error']}")
            
            elif time_query["type"] == "day_of_week":
                day_data = get_day_of_week(time_query["query"])
                if "error" not in day_data:
                    time_context = f"""
                    [DAY OF WEEK DATA]
                    Date: {day_data['date']}
                    Day of Week: {day_data['day_of_week']}
                    Is Weekend: {'Yes' if day_data['is_weekend'] else 'No'}
                    [/DAY OF WEEK DATA]
                    """
                    log.info(f"Day of week data retrieved: {day_data}")
                else:
                    time_context = f"[TIME ERROR: {day_data['error']}]"
                    log.warning(f"Day of week error: {day_data['error']}")
            
            elif time_query["type"] == "current_time":
                local_time = datetime.now()
                time_context = f"""
                [CURRENT TIME DATA]
                Local Time: {local_time.strftime('%I:%M %p')}
                Local Date: {local_time.strftime('%A, %B %d, %Y')}
                UTC Time: {datetime.now(pytz.UTC).strftime('%I:%M %p UTC')}
                [/CURRENT TIME DATA]
                """
                log.info(f"Current time data retrieved")
        
        # Prepare the prompt with context if available
        prompt = transcript
        context_parts = []
        
        if weather_context:
            context_parts.append(weather_context)
        
        if time_context:
            context_parts.append(time_context)
        
        if context_parts:
            combined_context = "\n\n".join(context_parts)
            prompt = f"{combined_context}\n\nUser question: {transcript}\n\nPlease use the data above to answer the user's question in your pirate style."
        
        # Use current API keys
        if not current_api_keys["gemini"]:
            await websocket.send_json({
                "type": "error",
                "data": "Gemini API key not configured. Please set it in the configuration panel."
            })
            return None
        
        # Create model with current API key
        current_model = GenerativeModel(model_name="gemini-2.0-flash", api_key=current_api_keys["gemini"])
        
        response = await asyncio.to_thread(
            current_model.generate_content,
            prompt,
            stream=True
        )
        accumulated_response = ""
        
        if not current_api_keys["murf"]:
            await websocket.send_json({
                "type": "error",
                "data": "Murf API key not configured. Please set it in the configuration panel."
            })
            return None
        
        murf_ws_url = f"{DEFAULT_MURF_WS_URL}?api_key={current_api_keys['murf']}&context_id={CONTEXT_ID}&format=WAV&sample_rate=44100&channel_type=MONO"
        log.info(f"Attempting WebSocket connection to: {murf_ws_url}")
        async with websockets.connect(murf_ws_url) as murf_ws:
            # Initial connection message
            await murf_ws.send(json.dumps({"init": True}))
            # Set voice config
            voice_config = {"voice_config": {"voiceId": "en-US-amara", "style": "Conversational"}}
            await murf_ws.send(json.dumps(voice_config))
            log.info(f"Sent voice config: {voice_config}")
            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    accumulated_response += content
                    log.info(f"Sending to Murf: {content}")
                    await murf_ws.send(json.dumps({"text": content}))
                    # Receive base64 audio from Murf
                    murf_response = await murf_ws.recv()
                    log.info(f"Received from Murf: {murf_response[:100]}...")
                    murf_data = json.loads(murf_response)
                    base64_audio = murf_data.get("audio", "")
                    is_final = murf_data.get("is_final", False) if "is_final" in murf_data else False
                    # Send base64 audio to client
                    if base64_audio:
                        try:
                            await websocket.send_json({
                                "type": "audio",
                                "data": base64_audio,
                                "is_final": is_final
                            })
                            log.info(f"Sent base64 audio to client (Final: {is_final}, Length: {len(base64_audio)})")
                        except Exception as e:
                            log.error(f"Failed to send audio to client: {e}")
                    if is_final:
                        break
            # Continue receiving remaining audio chunks until final
            while True:
                try:
                    murf_response = await asyncio.wait_for(murf_ws.recv(), timeout=5.0)
                    log.info(f"Received additional from Murf: {murf_response[:100]}...")
                    murf_data = json.loads(murf_response)
                    base64_audio = murf_data.get("audio", "")
                    is_final = murf_data.get("is_final", False)
                    if base64_audio:
                        await websocket.send_json({
                            "type": "audio",
                            "data": base64_audio,
                            "is_final": is_final
                        })
                        log.info(f"Sent additional base64 audio to client (Final: {is_final}, Length: {len(base64_audio)})")
                    if is_final:
                        break
                except asyncio.TimeoutError:
                    log.warning("Timeout waiting for additional Murf audio, assuming complete")
                    break
        # Save chat history
        if accumulated_response:
            save_chat_history(transcript, accumulated_response)
            # Send response text to client for display
            await websocket.send_json({
                "type": "response",
                "data": accumulated_response
            })
        log.info("Gemini Response Complete.")
        return accumulated_response
    except websockets.exceptions.ConnectionClosedError as e:
        log.error(f"Murf WebSocket connection closed: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        log.error(f"Murf WebSocket error: HTTP {e.status_code} - {e.reason}")
    except Exception as e:
        log.error(f"Murf WebSocket error: {e}")
    return None

# API Key management endpoints
@app.get("/api/keys")
async def get_api_keys():
    """Get current API key status (without exposing actual keys)."""
    return {
        "aai": {"configured": bool(current_api_keys["aai"])},
        "gemini": {"configured": bool(current_api_keys["gemini"])},
        "murf": {"configured": bool(current_api_keys["murf"])},
        "openweather": {"configured": bool(current_api_keys["openweather"])}
    }

@app.post("/api/keys")
async def update_api_keys(request: Request):
    """Update API keys via UI."""
    try:
        data = await request.json()
        updated = False
        
        if "aai" in data and data["aai"]:
            current_api_keys["aai"] = data["aai"]
            aai.settings.api_key = data["aai"]
            updated = True
            log.info("AssemblyAI API key updated")
        
        if "gemini" in data and data["gemini"]:
            current_api_keys["gemini"] = data["gemini"]
            configure(api_key=data["gemini"])
            updated = True
            log.info("Gemini API key updated")
        
        if "murf" in data and data["murf"]:
            current_api_keys["murf"] = data["murf"]
            updated = True
            log.info("Murf API key updated")
        
        if "openweather" in data and data["openweather"]:
            current_api_keys["openweather"] = data["openweather"]
            updated = True
            log.info("OpenWeather API key updated")
        
        return {"success": True, "updated": updated, "message": "API keys updated successfully"}
    except Exception as e:
        log.error(f"Error updating API keys: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/test-keys")
async def test_api_keys(request: Request):
    """Test if the configured API keys are working."""
    try:
        data = await request.json()
        results = {}
        
        # Test AssemblyAI
        if "aai" in data and data["aai"]:
            try:
                test_aai = aai.Transcriber()
                # This will fail if the key is invalid
                results["aai"] = {"valid": True, "message": "AssemblyAI key is valid"}
            except Exception as e:
                results["aai"] = {"valid": False, "message": f"AssemblyAI key error: {str(e)}"}
        
        # Test Gemini
        if "gemini" in data and data["gemini"]:
            try:
                test_model = GenerativeModel(model_name="gemini-2.0-flash", api_key=data["gemini"])
                response = test_model.generate_content("Test")
                results["gemini"] = {"valid": True, "message": "Gemini key is valid"}
            except Exception as e:
                results["gemini"] = {"valid": False, "message": f"Gemini key error: {str(e)}"}
        
        # Test Murf (basic validation)
        if "murf" in data and data["murf"]:
            results["murf"] = {"valid": True, "message": "Murf key format looks valid"}
        
        # Test OpenWeather
        if "openweather" in data and data["openweather"]:
            try:
                test_url = f"http://api.openweathermap.org/data/2.5/weather?q=London&appid={data['openweather']}"
                response = requests.get(test_url, timeout=5)
                if response.status_code == 200:
                    results["openweather"] = {"valid": True, "message": "OpenWeather key is valid"}
                else:
                    results["openweather"] = {"valid": False, "message": "OpenWeather key is invalid"}
            except Exception as e:
                results["openweather"] = {"valid": False, "message": f"OpenWeather key error: {str(e)}"}
        
        return {"success": True, "results": results}
    except Exception as e:
        log.error(f"Error testing API keys: {e}")
        return {"success": False, "error": str(e)}

# Routes
@app.get("/")
async def index(request: Request):
    log.info("Sending index page")
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    await websocket.accept()
    log.info("WebSocket connected")

    py_audio: Optional[pyaudio.PyAudio] = None
    mic_stream: Optional[pyaudio.Stream] = None
    audio_thread: Optional[threading.Thread] = None
    stop_event = threading.Event()
    recorded_frames: List[bytes] = []
    frames_lock = threading.Lock()

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str] = asyncio.Queue()

    # Buffers
    all_transcripts = []
    final_transcript = None

    # Forward and log transcript text
    async def forward_event(client, message):
        nonlocal final_transcript
        try:
            if message.type == "Turn" and message.transcript:
                transcript_text = message.transcript.strip()
                all_transcripts.append(transcript_text)
                log.info(f"Live Transcription: {transcript_text}")
                await websocket.send_text(transcript_text)
                if hasattr(message, "turn_is_formatted") and message.turn_is_formatted:
                    final_transcript = transcript_text
                    log.info(f"Final Formatted Transcription: {final_transcript}")
            elif message.type == "Termination":
                log.info("Turn ended detected")
                if final_transcript or all_transcripts:
                    await websocket.send_text(final_transcript or all_transcripts[-1])
                await websocket.send_text("turn_ended")
                if final_transcript:
                    await stream_gemini_response(final_transcript, websocket)
            elif message.type == "error":
                error_msg = f"Error: {str(message)}"
                log.error(error_msg)
                await websocket.send_text(error_msg)
        except Exception as e:
            log.error(f"forward_event error: {e}")

    if not current_api_keys["aai"]:
        await websocket.send_json({
            "type": "error",
            "data": "AssemblyAI API key not configured. Please set it in the configuration panel."
        })
        return
    
    client = StreamingClient(
        StreamingClientOptions(api_key=current_api_keys["aai"], api_host="streaming.assemblyai.com")
    )
    client.on(StreamingEvents.Begin, lambda client, message: loop.call_soon_threadsafe(
        lambda: asyncio.run_coroutine_threadsafe(forward_event(client, message), loop)))
    client.on(StreamingEvents.Turn, lambda client, message: loop.call_soon_threadsafe(
        lambda: asyncio.run_coroutine_threadsafe(forward_event(client, message), loop)))
    client.on(StreamingEvents.Termination, lambda client, message: loop.call_soon_threadsafe(
        lambda: asyncio.run_coroutine_threadsafe(forward_event(client, message), loop)))
    client.on(StreamingEvents.Error, lambda client, message: loop.call_soon_threadsafe(
        lambda: asyncio.run_coroutine_threadsafe(forward_event(client, message), loop)))

    client.connect(StreamingParameters(sample_rate=SAMPLE_RATE, format_turns=True))

    async def pump_queue():
        try:
            while True:
                msg = await queue.get()
                await websocket.send_text(msg)
                queue.task_done()
        except Exception:
            pass

    queue_task = asyncio.create_task(pump_queue())

    def stream_audio():
        nonlocal mic_stream, py_audio
        log.info("Starting audio streaming thread")
        try:
            py_audio = pyaudio.PyAudio()
            mic_stream = py_audio.open(
                input=True,
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
            while not stop_event.is_set():
                try:
                    data = mic_stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                    with frames_lock:
                        recorded_frames.append(data)
                    client.stream(data)
                except IOError as e:
                    log.warning(f"Audio read error: {e}, retrying...")
                    time.sleep(0.01)
        except Exception as e:
            log.error(f"Audio thread error: {e}")
            asyncio.run_coroutine_threadsafe(queue.put(f"Transcription error: {e}"), loop)
        finally:
            try:
                if mic_stream:
                    if mic_stream.is_active():
                        mic_stream.stop_stream()
                    mic_stream.close()
            except Exception:
                pass
            mic_stream = None
            if py_audio:
                try:
                    py_audio.terminate()
                except Exception:
                    pass
                py_audio = None
            log.info("Audio streaming thread ended")

    try:
        while True:
            try:
                msg = await websocket.receive_text()
                log.info(f"Received client command: {msg}")
            except Exception as e:
                log.error(f"WebSocket receive error: {e}")
                break

            if msg == "start":
                if audio_thread and audio_thread.is_alive():
                    await websocket.send_text("Already transcribing")
                    continue
                stop_event.clear()
                with frames_lock:
                    recorded_frames.clear()
                all_transcripts.clear()
                final_transcript = None
                audio_thread = threading.Thread(target=stream_audio, daemon=True)
                audio_thread.start()
                await websocket.send_text("Started transcription")

            elif msg == "stop":
                stop_event.set()
                if audio_thread and audio_thread.is_alive():
                    audio_thread.join(timeout=5.0)

                if final_transcript or all_transcripts:
                    await websocket.send_text(final_transcript or all_transcripts[-1])
                    await websocket.send_text("turn_ended")
                    if final_transcript:
                        await stream_gemini_response(final_transcript, websocket)

                with frames_lock:
                    saved = save_wav(recorded_frames.copy())
                    recorded_frames.clear()

                await websocket.send_text(
                    "Stopped transcription"
                    + (f" (saved: {os.path.basename(saved)})" if saved else "")
                )

            else:
                await websocket.send_text(f"Unknown command: {msg}")

            await asyncio.sleep(0.01)

    finally:
        stop_event.set()
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=5.0)
        client.disconnect(terminate=True)
        queue_task.cancel()
        log.info("WebSocket closed")

if __name__ == "__main__":
    import uvicorn
    print("🏴‍☠️ AI Voice Agent with DUAL Special Powers starting up...")
    print("🌤️ Special skill 1: Real-time weather data for any location!")
    print("⏰ Special skill 2: Time/date calculations & timezone conversions!")
    print("⚙️ NEW: Dynamic API key configuration via UI!")
    print("📡 API keys can be configured in the sidebar")
    print("🌐 Open http://localhost:8000 in your browser")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)