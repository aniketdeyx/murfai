// Global variables
let ws = null;
let audioContext = null;
let audioQueue = [];
let isPlaying = false;
let nextStartTime = 0;
let isFirstAudio = true;

const SAMPLE_RATE = 44100; // Murf output sample rate
const CHANNELS = 1;
const BITS_PER_SAMPLE = 16;

// DOM elements
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const retryBtn = document.getElementById("retryBtn");
const status = document.getElementById("status");
const transcriptionText = document.getElementById("transcriptionText");
const chatHistory = document.getElementById("chatHistory");
const connectionStatus = document.getElementById("connectionStatus");

// Sidebar elements
const sidebar = document.getElementById("sidebar");
const configToggle = document.getElementById("configToggle");
const closeSidebar = document.getElementById("closeSidebar");
const mainContent = document.querySelector(".main-content");

// Configuration elements
const aaiKeyInput = document.getElementById("aaiKey");
const geminiKeyInput = document.getElementById("geminiKey");
const murfKeyInput = document.getElementById("murfKey");
const saveConfigBtn = document.getElementById("saveConfig");
const testAllBtn = document.getElementById("testAll");
const clearTranscriptionBtn = document.getElementById("clearTranscription");
const clearHistoryBtn = document.getElementById("clearHistory");

// Toast container
const toastContainer = document.getElementById("toastContainer");

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    loadApiKeyStatus();
    connectWebSocket();
    fetchChatHistory();
}

// Event Listeners
function setupEventListeners() {
    // Sidebar controls
    configToggle.addEventListener("click", toggleSidebar);
    closeSidebar.addEventListener("click", closeSidebarPanel);
    
    // Configuration
    saveConfigBtn.addEventListener("click", saveConfiguration);
    testAllBtn.addEventListener("click", testAllApiKeys);
    
    // Individual API key testing
    document.querySelectorAll('.test-btn').forEach(btn => {
        btn.addEventListener("click", (e) => testApiKey(e.target.closest('.api-key-group').querySelector('input').id.replace('Key', '')));
    });
    
    // Control buttons
    startBtn.addEventListener("click", startTranscription);
    stopBtn.addEventListener("click", stopTranscription);
    retryBtn.addEventListener("click", retryConnection);
    
    // Clear buttons
    clearTranscriptionBtn.addEventListener("click", clearTranscription);
    clearHistoryBtn.addEventListener("click", clearChatHistory);
    
    // Close sidebar when clicking outside
    document.addEventListener("click", (e) => {
        if (!sidebar.contains(e.target) && !configToggle.contains(e.target) && sidebar.classList.contains('open')) {
            closeSidebarPanel();
        }
    });
}

// Sidebar Management
function toggleSidebar() {
    sidebar.classList.toggle('open');
    mainContent.classList.toggle('sidebar-open');
}

function closeSidebarPanel() {
    sidebar.classList.remove('open');
    mainContent.classList.remove('sidebar-open');
}

// API Key Management
async function loadApiKeyStatus() {
    try {
        const response = await fetch("/api/keys");
        const keys = await response.json();
        
        // Update status indicators
        Object.keys(keys).forEach(service => {
            const statusElement = document.getElementById(`${service}Status`);
            if (statusElement) {
                if (keys[service].configured) {
                    statusElement.textContent = "✓ Configured";
                    statusElement.className = "status-indicator success";
                } else {
                    statusElement.textContent = "⚠ Not configured";
                    statusElement.className = "status-indicator warning";
                }
            }
        });
    } catch (error) {
        console.error("Error loading API key status:", error);
        showToast("Error loading API key status", "error");
    }
}

async function saveConfiguration() {
    const config = {
        aai: aaiKeyInput.value.trim(),
        gemini: geminiKeyInput.value.trim(),
        murf: murfKeyInput.value.trim()
    };
    
    try {
        const response = await fetch("/api/keys", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast("Configuration saved successfully!", "success");
            loadApiKeyStatus();
            
            // Reconnect WebSocket with new keys
            if (ws) {
                ws.close();
            }
            setTimeout(connectWebSocket, 1000);
        } else {
            showToast(`Error: ${result.error}`, "error");
        }
    } catch (error) {
        console.error("Error saving configuration:", error);
        showToast("Error saving configuration", "error");
    }
}

async function testApiKey(service) {
    const inputElement = document.getElementById(`${service}Key`);
    const key = inputElement.value.trim();
    
    if (!key) {
        showToast(`Please enter a ${service.toUpperCase()} API key first`, "warning");
        return;
    }
    
    try {
        const response = await fetch("/api/test-keys", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ [service]: key })
        });
        
        const result = await response.json();
        
        if (result.success && result.results[service]) {
            const testResult = result.results[service];
            const statusElement = document.getElementById(`${service}Status`);
            
            if (testResult.valid) {
                statusElement.textContent = `✓ ${testResult.message}`;
                statusElement.className = "status-indicator success";
                showToast(`${service.toUpperCase()} API key is valid!`, "success");
            } else {
                statusElement.textContent = `✗ ${testResult.message}`;
                statusElement.className = "status-indicator error";
                showToast(`${service.toUpperCase()} API key is invalid: ${testResult.message}`, "error");
            }
        } else {
            showToast(`Error testing ${service.toUpperCase()} API key`, "error");
        }
    } catch (error) {
        console.error(`Error testing ${service} API key:`, error);
        showToast(`Error testing ${service.toUpperCase()} API key`, "error");
    }
}

async function testAllApiKeys() {
    const config = {
        aai: aaiKeyInput.value.trim(),
        gemini: geminiKeyInput.value.trim(),
        murf: murfKeyInput.value.trim()
    };
    
    const servicesToTest = Object.keys(config).filter(key => config[key]);
    
    if (servicesToTest.length === 0) {
        showToast("Please enter at least one API key to test", "warning");
        return;
    }
    
    showToast("Testing all API keys...", "warning");
    
    try {
        const response = await fetch("/api/test-keys", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success) {
            let allValid = true;
            let message = "API Key Test Results:\n";
            
            Object.keys(result.results).forEach(service => {
                const testResult = result.results[service];
                const statusElement = document.getElementById(`${service}Status`);
                
                if (testResult.valid) {
                    statusElement.textContent = `✓ ${testResult.message}`;
                    statusElement.className = "status-indicator success";
                    message += `✓ ${service.toUpperCase()}: Valid\n`;
                } else {
                    statusElement.textContent = `✗ ${testResult.message}`;
                    statusElement.className = "status-indicator error";
                    message += `✗ ${service.toUpperCase()}: Invalid\n`;
                    allValid = false;
                }
            });
            
            if (allValid) {
                showToast("All API keys are valid! 🎉", "success");
            } else {
                showToast("Some API keys are invalid. Please check the configuration.", "error");
            }
        } else {
            showToast(`Error testing API keys: ${result.error}`, "error");
        }
    } catch (error) {
        console.error("Error testing API keys:", error);
        showToast("Error testing API keys", "error");
    }
}

// WebSocket Management
function connectWebSocket() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${scheme}://${window.location.host}/ws`);

    ws.onopen = () => {
        console.log("WebSocket opened");
        updateConnectionStatus("Connected to server ✅", "connected");
        startBtn.disabled = false;
    };

    ws.onmessage = async (event) => {
        const data = event.data;
        console.log("WebSocket message received:", data.substring(0, 100) + "...");

        // Handle JSON messages (audio or response)
        if (data.startsWith("{")) {
            try {
                const jsonData = JSON.parse(data);
                if (jsonData.type === "audio" && jsonData.data) {
                    console.log("Audio chunk received, is_final:", jsonData.is_final, "length:", jsonData.data.length);
                    await queueAudio(jsonData.data, jsonData.is_final);
                } else if (jsonData.type === "response" && jsonData.data) {
                    appendToTranscription(`AI: ${jsonData.data}`);
                    await fetchChatHistory();
                } else if (jsonData.type === "error" && jsonData.data) {
                    showToast(jsonData.data, "error");
                    updateStatus("Error occurred ❌");
                } else {
                    console.warn("Invalid JSON message format:", jsonData);
                }
            } catch (e) {
                console.error("Error parsing JSON message:", e);
                updateStatus("Error: Invalid data received ❌");
            }
            return;
        }

        // Handle text messages
        handleTextMessage(data);
    };

    ws.onclose = () => {
        console.log("WebSocket closed");
        updateConnectionStatus("Disconnected from server 🔌", "disconnected");
        startBtn.disabled = true;
        stopBtn.style.display = "none";
        retryBtn.style.display = "inline-block";
        updateStatus("Status: Disconnected 🔌");
    };

    ws.onerror = () => {
        updateConnectionStatus("Error connecting to server ❌", "disconnected");
        startBtn.disabled = true;
    };
}

function handleTextMessage(data) {
    if (data === "Started transcription") {
        updateStatus("Status: Transcribing 🎤");
        clearTranscriptionText();
        startBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
        retryBtn.style.display = "none";
    } else if (data === "turn_ended") {
        updateStatus("Status: Processing response 🤖");
    } else if (data.startsWith("Stopped transcription")) {
        updateStatus("Status: Idle ⏳");
        startBtn.style.display = "inline-block";
        stopBtn.style.display = "none";
        retryBtn.style.display = "inline-block";
        if (data.includes("saved")) {
            const filename = data.match(/saved: (.+)$/)[1];
            appendToTranscription(`Audio saved as ${filename}`);
        }
    } else if (data.startsWith("Error:") || data.startsWith("Transcription error:")) {
        updateStatus(`Error: ${data}`);
        startBtn.style.display = "inline-block";
        stopBtn.style.display = "none";
        retryBtn.style.display = "inline-block";
        showToast(data, "error");
    } else if (data === "Already transcribing") {
        updateStatus("Status: Already transcribing 🎤");
    } else {
        // Append transcription text
        appendToTranscription(data);
    }
}

// Audio Management
function initAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: SAMPLE_RATE,
        });
        console.log("AudioContext initialized, sampleRate:", audioContext.sampleRate);
    }
}

function base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

async function queueAudio(base64Audio, isFinal) {
    try {
        let pcmBuffer = base64ToArrayBuffer(base64Audio);
        if (isFirstAudio) {
            console.log("First audio chunk: skipping 44-byte WAV header");
            pcmBuffer = pcmBuffer.slice(44);
            isFirstAudio = false;
        }

        const int16 = new Int16Array(pcmBuffer);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768;
        }

        const audioBuffer = audioContext.createBuffer(CHANNELS, float32.length, SAMPLE_RATE);
        audioBuffer.copyToChannel(float32, 0);

        console.log("Audio chunk processed, duration:", audioBuffer.duration, "isFinal:", isFinal);
        audioQueue.push({ buffer: audioBuffer, isFinal });
        playNextAudio();
    } catch (error) {
        console.error("Error processing audio:", error);
        updateStatus("Error: Failed to play audio ❌");
    }
}

function playNextAudio() {
    if (isPlaying || audioQueue.length === 0) return;

    isPlaying = true;
    const { buffer, isFinal } = audioQueue.shift();
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    const currentTime = audioContext.currentTime;
    source.start(Math.max(nextStartTime, currentTime));
    nextStartTime = Math.max(nextStartTime, currentTime) + buffer.duration;

    source.onended = () => {
        isPlaying = false;
        if (isFinal) {
            audioQueue = [];
            nextStartTime = 0;
            isFirstAudio = true;
            console.log("Audio playback complete");
            updateStatus("Status: Audio playback complete ✅");
        } else {
            playNextAudio();
        }
    };
}

// Control Functions
function startTranscription() {
    initAudioContext();
    isFirstAudio = true;
    ws.send("start");
}

function stopTranscription() {
    ws.send("stop");
}

function retryConnection() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("start");
    } else {
        connectWebSocket();
        updateStatus("Status: Reconnecting... 🔄");
    }
}

// UI Update Functions
function updateStatus(message) {
    const statusSpan = status.querySelector("span");
    statusSpan.textContent = message;
}

function updateConnectionStatus(message, className) {
    connectionStatus.textContent = message;
    connectionStatus.className = `connection-status ${className}`;
}

function appendToTranscription(text) {
    if (transcriptionText.textContent === "") {
        transcriptionText.textContent = text;
    } else {
        transcriptionText.textContent += "\n" + text;
    }
    transcriptionText.scrollTop = transcriptionText.scrollHeight;
}

function clearTranscriptionText() {
    transcriptionText.textContent = "";
}

function clearTranscription() {
    clearTranscriptionText();
    showToast("Transcription cleared", "success");
}

async function clearChatHistory() {
    try {
        const response = await fetch("/chat_history", {
            method: "DELETE"
        });
        if (response.ok) {
            chatHistory.innerHTML = '<div class="loading-message"><i class="fas fa-spinner fa-spin"></i><span>No chat history</span></div>';
            showToast("Chat history cleared", "success");
        }
    } catch (error) {
        console.error("Error clearing chat history:", error);
        showToast("Error clearing chat history", "error");
    }
}

// Chat History Management
async function fetchChatHistory() {
    try {
        const response = await fetch("/chat_history");
        const history = await response.json();
        
        if (Array.isArray(history)) {
            if (history.length > 0) {
                chatHistory.innerHTML = history
                    .map(entry => `
                        <div class="chat-entry">
                            <div class="timestamp">${new Date(entry.timestamp).toLocaleString()}</div>
                            <div class="user-query">You: ${entry.user_query}</div>
                            <div class="ai-response">AI: ${entry.ai_response}</div>
                        </div>
                    `)
                    .join("");
            } else {
                chatHistory.innerHTML = '<div class="loading-message"><i class="fas fa-comments"></i><span>No chat history yet</span></div>';
            }
        } else {
            chatHistory.innerHTML = '<div class="loading-message"><i class="fas fa-exclamation-triangle"></i><span>Error loading chat history</span></div>';
        }
    } catch (error) {
        console.error("Error fetching chat history:", error);
        chatHistory.innerHTML = '<div class="loading-message"><i class="fas fa-exclamation-triangle"></i><span>Error loading chat history</span></div>';
    }
}

// Toast Notifications
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
    
    // Remove on click
    toast.addEventListener("click", () => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    });
}