# AI Voice Agent with Dual Powers (Weather + Time) 🏴‍☠️🌤️⏰

A voice-enabled AI assistant with a pirate personality that can provide real-time weather information and time/date calculations with timezone conversions.

## Features

- **Voice Interaction**: Real-time speech-to-text using AssemblyAI
- **AI Responses**: Powered by Google Gemini with a pirate personality
- **Text-to-Speech**: Natural voice responses using Murf
- **Weather Powers**: Get real-time weather data for any location worldwide
- **Time Powers**: Timezone conversions, date differences, day-of-week, and countdowns
- **Dynamic API Config**: Enter and test API keys via the UI (no .env edits required)
- **Chat History**: Persistent conversation history

## Special Weather Skill

The agent can understand weather-related questions like:
- "What's the weather like in New York?"
- "How's the weather in Tokyo?"
- "Check weather for London"
- "Temperature in Paris"

## Local Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables** (create a `.env` file):
   ```
   AAI_API_KEY=your_assemblyai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   MURF_API_KEY=your_murf_api_key_here
   OPENWEATHER_API_KEY=your_openweathermap_api_key_here
   ```

3. **Get API Keys**:
   - [AssemblyAI](https://www.assemblyai.com/) - Speech-to-text
   - [Google AI Studio](https://aistudio.google.com/) - Gemini API
   - [Murf](https://murf.ai/) - Text-to-speech
   - [OpenWeatherMap](https://openweathermap.org/api) - Weather data (free tier available)

4. **Run the application**:
   ```bash
   python main.py
   ```

5. **Open your browser** and go to `http://localhost:8000`

## Usage

1. Open the sidebar (gear icon) and paste your API keys (AssemblyAI, Gemini, Murf). Save.
2. Click "Start Transcription" to begin voice interaction
2. Ask questions naturally - the agent will respond in pirate style
3. Try weather: "What's the weather in San Francisco?"
4. Try time: "What time is it in Tokyo?" or "How many days until Christmas?"
5. Click "Stop Transcription" when done

## Weather Data Provided

- Current temperature (°C)
- "Feels like" temperature
- Weather conditions (sunny, cloudy, etc.)
- Humidity percentage
- Wind speed (km/h)
- Atmospheric pressure (hPa)

## Deploy to Render (Free Tier)

1. Push this repo to GitHub
2. Create account at `https://render.com`
3. New → Blueprint → Select your repo
4. Render will detect `render.yaml`. Keep plan as Free.
5. Set environment variables (optional; users can also add via UI):
   - `AAI_API_KEY`, `GEMINI_API_KEY`, `MURF_API_KEY`, `MURF_WS_URL`
6. Click Deploy. Your app will be available at a public URL.

Notes:
- WebSocket auto-selects `wss://` in production.
- A 1GB persistent disk is mounted at `/uploads` for recordings and chat history.

## Endpoints
- `GET /` UI
- `WS /ws` audio streaming
- `GET /chat_history` and `DELETE /chat_history`
- `GET /api/keys`, `POST /api/keys` (update keys), `POST /api/test-keys`

