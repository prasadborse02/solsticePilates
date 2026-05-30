"""Minimal web UI for Solstice Pilates AI Receptionist."""

import json
from flask import Flask, request, jsonify, render_template_string
from agent import ReceptionistAgent, TOOL_FUNCTIONS

app = Flask(__name__)

# Store agents per session (simple in-memory approach)
agents = {}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Solstice Pilates — Receptionist</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            padding: 16px 24px;
            background: #1a1a1a;
            border-bottom: 1px solid #2a2a2a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-left h1 { font-size: 18px; font-weight: 600; }
        .header-left p { font-size: 12px; color: #888; margin-top: 2px; }
        #mode-toggle {
            display: flex;
            gap: 4px;
            background: #0f0f0f;
            border-radius: 8px;
            padding: 3px;
        }
        #mode-toggle button {
            padding: 6px 14px;
            border-radius: 6px;
            border: none;
            font-size: 13px;
            cursor: pointer;
            background: transparent;
            color: #888;
        }
        #mode-toggle button.active {
            background: #2563eb;
            color: white;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .msg {
            max-width: 75%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .msg.user {
            align-self: flex-end;
            background: #2563eb;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .msg.agent {
            align-self: flex-start;
            background: #1e1e1e;
            border: 1px solid #333;
            border-bottom-left-radius: 4px;
        }
        .msg.system {
            align-self: center;
            color: #666;
            font-size: 12px;
        }
        /* Text input area */
        #input-area {
            padding: 16px 24px;
            background: #1a1a1a;
            border-top: 1px solid #2a2a2a;
            display: flex;
            gap: 8px;
        }
        #input {
            flex: 1;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #333;
            background: #0f0f0f;
            color: #e0e0e0;
            font-size: 14px;
            outline: none;
        }
        #input:focus { border-color: #2563eb; }
        #send {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            background: #2563eb;
            color: white;
            font-size: 14px;
            cursor: pointer;
        }
        #send:hover { background: #1d4ed8; }
        #send:disabled { opacity: 0.5; cursor: not-allowed; }
        .typing { color: #888; font-style: italic; }
        /* Voice area */
        #voice-area {
            padding: 32px 24px;
            background: #1a1a1a;
            border-top: 1px solid #2a2a2a;
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 16px;
        }
        #mic-btn {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: none;
            background: #2563eb;
            color: white;
            font-size: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        #mic-btn:hover { background: #1d4ed8; transform: scale(1.05); }
        #mic-btn.active {
            background: #dc2626;
            animation: pulse 1.5s infinite;
        }
        #mic-btn.active:hover { background: #b91c1c; }
        #voice-status {
            font-size: 14px;
            color: #888;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
            50% { box-shadow: 0 0 0 15px rgba(220, 38, 38, 0); }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <h1>Solstice Pilates</h1>
            <p>AI Receptionist</p>
        </div>
        <div id="mode-toggle">
            <button class="active" onclick="setMode('text')">Text</button>
            <button onclick="setMode('voice')">Voice</button>
        </div>
    </header>
    <div id="messages"></div>
    <!-- Text mode -->
    <div id="input-area">
        <input id="input" type="text" placeholder="Type a message..." autocomplete="off" />
        <button id="send" onclick="sendMessage()">Send</button>
    </div>
    <!-- Voice mode -->
    <div id="voice-area">
        <button id="mic-btn" onclick="toggleCall()">&#x1F3A4;</button>
        <div id="voice-status">Click to start a call</div>
    </div>

    <script type="module">
        import VapiModule from 'https://esm.sh/@vapi-ai/web@latest';
        const VapiClass = VapiModule.default || VapiModule;

        // --- Config ---
        const VAPI_PUBLIC_KEY = '77d554d6-582f-4586-972c-64d31d774d14';
        const VAPI_ASSISTANT_ID = 'eb014086-75fb-4ba9-8220-45a23e7ae956';

        // --- Text Chat ---
        const sessionId = Math.random().toString(36).substring(2);
        const messagesDiv = document.getElementById('messages');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('send');

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !sendBtn.disabled) sendMessage();
        });

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';
            sendBtn.disabled = true;

            const typing = document.createElement('div');
            typing.className = 'msg agent typing';
            typing.textContent = 'Typing...';
            messagesDiv.appendChild(typing);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: sessionId }),
                });
                const data = await res.json();
                typing.remove();
                addMessage(data.reply, 'agent');
            } catch (err) {
                typing.remove();
                addMessage('Something went wrong. Please try again.', 'system');
            }

            sendBtn.disabled = false;
            input.focus();
        }

        function addMessage(text, role) {
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.textContent = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // --- Mode Toggle ---
        let currentMode = 'text';
        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('#mode-toggle button').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            document.getElementById('input-area').style.display = mode === 'text' ? 'flex' : 'none';
            document.getElementById('voice-area').style.display = mode === 'voice' ? 'flex' : 'none';

            // Clear messages and show appropriate greeting
            messagesDiv.innerHTML = '';
            if (mode === 'text') {
                addMessage('Hi! Thanks for calling Solstice Pilates. How can I help you today?', 'agent');
                input.focus();
            }
        }

        // Show initial text greeting
        addMessage('Hi! Thanks for calling Solstice Pilates. How can I help you today?', 'agent');

        // --- Voice (Vapi) ---
        let vapi = null;
        let callActive = false;

        function initVapi() {
            if (vapi) return;
            if (VAPI_PUBLIC_KEY === '__VAPI_PUBLIC_KEY__') {
                addMessage('Voice mode not configured. Add your Vapi public key.', 'system');
                return false;
            }
            vapi = new VapiClass(VAPI_PUBLIC_KEY);

            vapi.on('call-start', () => {
                callActive = true;
                document.getElementById('mic-btn').classList.add('active');
                document.getElementById('voice-status').textContent = 'Connected — speak now';
                addMessage('Voice call started', 'system');
            });

            vapi.on('call-end', () => {
                callActive = false;
                document.getElementById('mic-btn').classList.remove('active');
                document.getElementById('voice-status').textContent = 'Call ended — click to start again';
                addMessage('Voice call ended', 'system');
            });

            vapi.on('message', (msg) => {
                if (msg.type === 'transcript' && msg.transcriptType === 'final') {
                    const text = msg.transcript.trim();
                    if (!text) return;
                    // Filter out endCall announcements
                    const lower = text.toLowerCase();
                    if (lower.includes('end call') || lower.includes('ending call')) return;

                    if (msg.role === 'user') {
                        addMessage(text, 'user');
                    } else if (msg.role === 'assistant') {
                        addMessage(text, 'agent');
                    }
                }
            });

            vapi.on('error', (e) => {
                console.error('Vapi error:', e);
                // Don't show error if call is ending normally
                if (!callActive) return;
                addMessage('Voice error: ' + (e.message || 'Unknown error'), 'system');
                callActive = false;
                document.getElementById('mic-btn').classList.remove('active');
                document.getElementById('voice-status').textContent = 'Error — click to retry';
            });

            return true;
        }

        function toggleCall() {
            if (!initVapi()) return;

            if (callActive) {
                vapi.stop();
                document.getElementById('voice-status').textContent = 'Ending call...';
            } else {
                vapi.start(VAPI_ASSISTANT_ID);
                document.getElementById('voice-status').textContent = 'Connecting...';
            }
        }

        // Expose functions to onclick handlers (module scope)
        window.sendMessage = sendMessage;
        window.setMode = setMode;
        window.toggleCall = toggleCall;

        input.focus();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"reply": "I didn't catch that. Could you say that again?"})

    # Get or create agent for this session
    if session_id not in agents:
        agents[session_id] = ReceptionistAgent()

    agent = agents[session_id]
    try:
        reply = agent.chat(message)
    except Exception as e:
        print(f"[error] {e}")
        if "429" in str(e):
            reply = "I'm a bit overwhelmed right now — give me a moment and try again!"
        else:
            reply = "Sorry, something went wrong on my end. Could you try again?"

    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json()
    session_id = data.get("session_id", "default")
    agents.pop(session_id, None)
    return jsonify({"status": "reset"})


# --- Vapi Webhook ---

@app.route("/vapi/webhook", methods=["POST"])
def vapi_webhook():
    """Handle incoming Vapi webhook events."""
    payload = request.get_json()

    # Log the full incoming payload for debugging
    print(f"[vapi] full payload: {json.dumps(payload, indent=2)}")

    message = payload.get("message", {})
    msg_type = message.get("type", "")

    print(f"[vapi] event type: {msg_type}")

    if msg_type == "tool-calls":
        tool_call_list = message.get("toolCallList", [])
        results = []

        for tool_call in tool_call_list:
            call_id = tool_call.get("id", "")
            fn_info = tool_call.get("function", {})
            fn_name = fn_info.get("name", "")
            fn_args = fn_info.get("arguments", {})

            print(f"[vapi] tool: {fn_name}({fn_args})")

            fn = TOOL_FUNCTIONS.get(fn_name)
            if not fn:
                results.append({"toolCallId": call_id, "result": json.dumps({"error": f"Unknown function: {fn_name}"})})
                continue

            try:
                result = fn(**fn_args)
            except Exception as e:
                print(f"[vapi] tool error: {e}")
                result = {"error": str(e)}

            results.append({"toolCallId": call_id, "result": json.dumps(result)})

        resp = {"results": results}
        print(f"[vapi] response: {json.dumps(resp)[:500]}")
        return jsonify(resp)

    if msg_type == "end-of-call-report":
        summary = message.get("summary", "No summary")
        print(f"[vapi] call ended: {summary}")
        return jsonify({})

    # For any other event type, just acknowledge
    return jsonify({})


if __name__ == "__main__":
    print("Starting Solstice Pilates Receptionist...")
    print("Open http://localhost:8080 in your browser\n")
    app.run(debug=False, host="0.0.0.0", port=8080)
