# AI Voice Agent with Dual Powers (Weather + Time) 🏴‍☠️🌤️⏰

A voice-enabled AI assistant with a pirate personality that can provide real-time weather information and time/date calculations with timezone conversions. Features a modern, responsive web interface with dynamic API key configuration.

## ✨ Features

### 🎤 Voice Interaction
- **Real-time Speech-to-Text**: Powered by AssemblyAI with live transcription
- **Natural Text-to-Speech**: High-quality voice responses using Murf AI
- **Streaming Audio**: Seamless audio streaming for real-time conversation
- **Local Audio Recording**: Automatic saving of conversation audio files

### 🤖 AI Intelligence
- **Google Gemini Integration**: Powered by Gemini 2.0 Flash for intelligent responses
- **Pirate Personality**: Engaging pirate-themed responses with nautical flair
- **Context-Aware**: Maintains conversation context and history
- **Real-time Processing**: Instant response generation and streaming

### 🌤️ Weather Powers
- **Global Weather Data**: Real-time weather information for any location worldwide
- **Comprehensive Data**: Temperature, feels-like, conditions, humidity, wind speed, pressure
- **Smart Location Detection**: Automatically extracts location names from natural language
- **Free API Integration**: Uses wttr.in API (no API key required for weather data)

### ⏰ Time Powers
- **Timezone Conversions**: Current time for 30+ major cities worldwide
- **Date Calculations**: Countdowns, date differences, and day-of-week calculations
- **Natural Language Processing**: Understands time-related queries in plain English
- **Comprehensive Time Data**: UTC offsets, local times, and formatted dates

### ⚙️ Dynamic Configuration
- **In-App API Key Management**: Configure all API keys through the web interface
- **Real-time Key Testing**: Test API keys individually or all at once
- **Secure Key Storage**: Keys are stored securely and can be updated without restart
- **No Environment File Required**: Complete setup possible through the UI

### 🎨 Modern User Interface
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Sidebar Configuration Panel**: Easy access to settings and API key management
- **Live Conversation Display**: Real-time transcription and AI response display
- **Chat History Management**: Persistent conversation history with clear functionality
- **Status Indicators**: Visual feedback for connection status and API key configuration
- **Toast Notifications**: User-friendly notifications for actions and errors

### 📊 Chat Management
- **Persistent Chat History**: Automatic saving of all conversations
- **History Viewing**: Browse through previous conversations
- **History Clearing**: Easy cleanup of conversation history
- **JSON Export**: Chat history stored in structured format

### 🔧 Technical Features
- **WebSocket Communication**: Real-time bidirectional communication
- **Audio Queue Management**: Smooth audio playback with proper queuing
- **Error Handling**: Comprehensive error handling and user feedback
- **Connection Management**: Automatic reconnection and status monitoring
- **File Management**: Automatic audio file organization and cleanup

## Special Weather Skill

The agent can understand weather-related questions like:
- "What's the weather like in New York?"
- "How's the weather in Tokyo?"
- "Check weather for London"
- "Temperature in Paris"
- "Weather forecast for Sydney"

## Special Time Skills

The agent can handle time-related queries like:
- "What time is it in Tokyo?"
- "How many days until Christmas?"
- "What day is January 15th, 2025?"
- "Current time in London"
- "Timezone for Dubai"
- "Countdown to New Year"

## 🚀 Local Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Optional: Set up environment variables** (create a `.env` file):
   ```
   AAI_API_KEY=your_assemblyai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   MURF_API_KEY=your_murf_api_key_here
   OPENWEATHER_API_KEY=your_openweathermap_api_key_here
   ```
   *Note: API keys can also be configured through the web interface*

3. **Get API Keys**:
   - [AssemblyAI](https://www.assemblyai.com/) - Speech-to-text (required)
   - [Google AI Studio](https://aistudio.google.com/) - Gemini API (required)
   - [Murf](https://murf.ai/) - Text-to-speech (required)
   - [OpenWeatherMap](https://openweathermap.org/api) - Weather data (optional, free tier available)

4. **Run the application**:
   ```bash
   python main.py
   ```

5. **Open your browser** and go to `http://localhost:8000`

## 🎯 Usage

### Initial Setup
1. Click the gear icon (⚙️) to open the configuration sidebar
2. Enter your API keys in the respective fields
3. Click "Test All Keys" to verify your configuration
4. Click "Save Configuration" to store your settings

### Voice Interaction
1. Click "Start Transcription" to begin voice interaction
2. Speak naturally - the agent will respond in pirate style
3. Try weather queries: "What's the weather in San Francisco?"
4. Try time queries: "What time is it in Tokyo?" or "How many days until Christmas?"
5. Click "Stop Transcription" when done

### Chat Management
- View your conversation history in the "Chat History" panel
- Clear individual conversations or entire history using the trash icon
- All conversations are automatically saved and persisted

## 🌤️ Weather Data Provided

- **Current temperature** (°C)
- **"Feels like" temperature** (°C)
- **Weather conditions** (sunny, cloudy, etc.)
- **Humidity percentage** (%)
- **Wind speed** (km/h)
- **Atmospheric pressure** (hPa)
- **Location information** (city, country)

## ⏰ Time Features

### Supported Timezones
- **Major Cities**: New York, London, Tokyo, Paris, Sydney, Mumbai, Singapore, Beijing, Dubai, Moscow, Berlin, Rome, Madrid, Amsterdam, Toronto, Vancouver, Mexico City, São Paulo, Buenos Aires, Cape Town, Cairo, Lagos, Nairobi
- **Date Calculations**: Countdowns, date differences, day-of-week calculations
- **Natural Language**: Understands queries like "how many days until Christmas" or "what day is January 15th"

## 🚀 Deploy to Render (Free Tier)

1. Push this repo to GitHub
2. Create account at `https://render.com`
3. New → Blueprint → Select your repo
4. Render will detect `render.yaml`. Keep plan as Free.
5. Set environment variables (optional; users can also add via UI):
   - `AAI_API_KEY`, `GEMINI_API_KEY`, `MURF_API_KEY`, `MURF_WS_URL`
6. Click Deploy. Your app will be available at a public URL.

### Deployment Notes:
- WebSocket auto-selects `wss://` in production
- A 1GB persistent disk is mounted at `/uploads` for recordings and chat history
- All API keys can be configured through the web interface after deployment

## 📡 API Endpoints

### Web Interface
- `GET /` - Main application interface

### WebSocket
- `WS /ws` - Real-time audio streaming and communication

### Chat History
- `GET /chat_history` - Retrieve conversation history
- `DELETE /chat_history` - Clear all conversation history

### API Key Management
- `GET /api/keys` - Get current API key configuration status
- `POST /api/keys` - Update API keys via UI
- `POST /api/test-keys` - Test API key validity

## 🛠️ Technical Architecture

### Frontend
- **HTML5**: Semantic markup with modern structure
- **CSS3**: Responsive design with gradients and animations
- **JavaScript**: ES6+ with async/await for real-time communication
- **WebSocket**: Real-time bidirectional communication
- **Web Audio API**: Audio playback and queue management

### Backend
- **FastAPI**: Modern Python web framework
- **WebSocket**: Real-time communication handling
- **AssemblyAI**: Speech-to-text streaming
- **Google Gemini**: AI response generation
- **Murf AI**: Text-to-speech synthesis
- **wttr.in**: Weather data API (free, no key required)

### Data Storage
- **JSON Files**: Chat history and configuration storage
- **WAV Files**: Audio recording storage
- **In-Memory**: Real-time API key management

## 🔒 Security Features

- **Secure API Key Storage**: Keys are stored securely in memory
- **Input Validation**: All user inputs are validated and sanitized
- **Error Handling**: Comprehensive error handling without exposing sensitive data
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 🎨 UI/UX Features

- **Responsive Design**: Works on all device sizes
- **Dark/Light Theme**: Modern gradient design
- **Smooth Animations**: CSS transitions and transforms
- **Status Indicators**: Visual feedback for all operations
- **Toast Notifications**: User-friendly feedback system
- **Loading States**: Visual indicators for async operations
- **Accessibility**: Proper ARIA labels and keyboard navigation

## 📝 Recent Updates

- **Dynamic API Configuration**: No more .env file editing required
- **Enhanced UI**: Modern sidebar configuration panel
- **Chat History Management**: Persistent conversation storage
- **Real-time Key Testing**: Validate API keys before use
- **Improved Error Handling**: Better user feedback and error recovery
- **Mobile Responsiveness**: Optimized for mobile devices
- **Audio File Management**: Automatic organization of recorded conversations

