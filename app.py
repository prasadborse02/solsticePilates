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
    <title>Solstice Pilates — AI Receptionist</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: #0a0a0a;
            color: #e4e4e7;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* --- Header --- */
        header {
            padding: 20px 32px;
            background: linear-gradient(135deg, #18181b 0%, #1e1b2e 100%);
            border-bottom: 1px solid rgba(139, 92, 246, 0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .logo {
            width: 42px; height: 42px;
            background: linear-gradient(135deg, #8b5cf6, #6d28d9);
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; font-weight: 700; color: white;
        }
        .header-left h1 {
            font-size: 20px; font-weight: 600;
            background: linear-gradient(135deg, #e4e4e7, #a78bfa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .header-left p { font-size: 12px; color: #71717a; margin-top: 2px; letter-spacing: 0.5px; text-transform: uppercase; }

        /* --- Mode Toggle --- */
        #mode-toggle {
            display: flex; gap: 2px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 3px;
        }
        #mode-toggle button {
            padding: 8px 18px; border-radius: 8px; border: none;
            font-size: 13px; font-weight: 500; cursor: pointer;
            background: transparent; color: #71717a;
            font-family: 'Inter', sans-serif; transition: all 0.2s;
        }
        #mode-toggle button.active {
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            color: white; box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
        }
        #mode-toggle button:hover:not(.active) { color: #a1a1aa; }

        /* --- Studio Info Bar --- */
        .info-bar {
            padding: 10px 32px;
            background: rgba(139, 92, 246, 0.06);
            border-bottom: 1px solid rgba(139, 92, 246, 0.08);
            display: flex; gap: 24px; align-items: center;
            font-size: 12px; color: #71717a;
        }
        .info-bar span { display: flex; align-items: center; gap: 6px; }
        .info-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; animation: blink 2s infinite; }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

        /* --- Messages --- */
        #messages {
            flex: 1; overflow-y: auto; padding: 28px 32px;
            display: flex; flex-direction: column; gap: 16px;
            scroll-behavior: smooth;
        }
        #messages::-webkit-scrollbar { width: 4px; }
        #messages::-webkit-scrollbar-track { background: transparent; }
        #messages::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }
        .msg {
            max-width: 70%; padding: 12px 18px;
            border-radius: 16px; font-size: 14px;
            line-height: 1.6; white-space: pre-wrap;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .msg.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            color: white; border-bottom-right-radius: 4px;
            box-shadow: 0 2px 12px rgba(124, 58, 237, 0.2);
        }
        .msg.agent {
            align-self: flex-start;
            background: #18181b;
            border: 1px solid #27272a;
            border-bottom-left-radius: 4px;
        }
        .msg.system {
            align-self: center; color: #52525b;
            font-size: 12px; font-weight: 500;
            background: rgba(255,255,255,0.03);
            padding: 6px 16px; border-radius: 20px;
        }
        .msg.agent::before {
            content: 'Solstice'; display: block;
            font-size: 11px; font-weight: 600; color: #8b5cf6;
            margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .msg.user::before {
            content: 'You'; display: block;
            font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.6);
            margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;
        }

        /* --- Text Input --- */
        #input-area {
            padding: 20px 32px;
            background: #18181b;
            border-top: 1px solid #27272a;
            display: flex; gap: 10px;
        }
        #input {
            flex: 1; padding: 14px 18px;
            border-radius: 12px; border: 1px solid #27272a;
            background: #0a0a0a; color: #e4e4e7;
            font-size: 14px; font-family: 'Inter', sans-serif;
            outline: none; transition: border-color 0.2s;
        }
        #input:focus { border-color: #7c3aed; box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1); }
        #input::placeholder { color: #3f3f46; }
        #send {
            padding: 14px 24px; border-radius: 12px; border: none;
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            color: white; font-size: 14px; font-weight: 500;
            cursor: pointer; font-family: 'Inter', sans-serif;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
        }
        #send:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); }
        #send:active { transform: translateY(0); }
        #send:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .typing {
            color: #71717a; font-style: italic;
            background: none !important; border: none !important;
            padding: 4px 0 !important;
        }
        .typing::before { content: none !important; }

        /* --- Voice Area --- */
        #voice-area {
            padding: 48px 32px;
            background: #18181b;
            border-top: 1px solid #27272a;
            display: none; flex-direction: column;
            align-items: center; gap: 20px;
        }
        .mic-container { position: relative; }
        .mic-ring {
            position: absolute; inset: -12px;
            border-radius: 50%; border: 2px solid rgba(124, 58, 237, 0.2);
            animation: none;
        }
        .mic-ring.active { animation: ringPulse 2s infinite; }
        @keyframes ringPulse {
            0%,100% { transform: scale(1); opacity: 0.3; }
            50% { transform: scale(1.15); opacity: 0; }
        }
        #mic-btn {
            width: 80px; height: 80px; border-radius: 50%; border: none;
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            color: white; font-size: 28px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.3s; position: relative; z-index: 1;
            box-shadow: 0 4px 20px rgba(124, 58, 237, 0.3);
        }
        #mic-btn:hover { transform: scale(1.05); box-shadow: 0 6px 24px rgba(124, 58, 237, 0.4); }
        #mic-btn.active {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
        }
        #voice-status { font-size: 14px; color: #71717a; font-weight: 500; }
        #voice-hint { font-size: 12px; color: #3f3f46; }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <div class="logo">S</div>
            <div>
                <h1>Solstice Pilates</h1>
                <p>AI Receptionist</p>
            </div>
        </div>
        <div id="mode-toggle">
            <button class="active" onclick="setMode('text')">Chat</button>
            <button onclick="setMode('voice')">Voice</button>
        </div>
    </header>
    <div class="info-bar">
        <span><span class="info-dot"></span> Online</span>
        <span>Mon-Sat 7AM-8PM, Sun 8AM-6PM</span>
        <span>(415) 555-0100</span>
    </div>
    <div id="messages"></div>
    <div id="input-area">
        <input id="input" type="text" placeholder="Ask about classes, booking, pricing..." autocomplete="off" />
        <button id="send" onclick="sendMessage()">Send</button>
    </div>
    <div id="voice-area">
        <div class="mic-container">
            <div class="mic-ring" id="mic-ring"></div>
            <button id="mic-btn" onclick="toggleCall()">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
            </button>
        </div>
        <div id="voice-status">Tap to start a voice call</div>
        <div id="voice-hint">Your mic will be used for the call</div>
    </div>

    <script type="module">
        import VapiModule from 'https://esm.sh/@vapi-ai/web@latest';
        const VapiClass = VapiModule.default || VapiModule;

        const VAPI_PUBLIC_KEY = '77d554d6-582f-4586-972c-64d31d774d14';
        const VAPI_ASSISTANT_ID = 'eb014086-75fb-4ba9-8220-45a23e7ae956';

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
            typing.textContent = 'Thinking...';
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
                addMessage('Connection issue. Please try again.', 'system');
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

        let currentMode = 'text';
        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('#mode-toggle button').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('input-area').style.display = mode === 'text' ? 'flex' : 'none';
            document.getElementById('voice-area').style.display = mode === 'voice' ? 'flex' : 'none';
            messagesDiv.innerHTML = '';
            if (mode === 'text') {
                addMessage('Hi! Welcome to Solstice Pilates. How can I help you today?', 'agent');
                input.focus();
            }
        }

        addMessage('Hi! Welcome to Solstice Pilates. How can I help you today?', 'agent');

        let vapi = null;
        let callActive = false;

        function initVapi() {
            if (vapi) return true;
            if (VAPI_PUBLIC_KEY === '__VAPI_PUBLIC_KEY__') {
                addMessage('Voice not configured.', 'system');
                return false;
            }
            vapi = new VapiClass(VAPI_PUBLIC_KEY);

            vapi.on('call-start', () => {
                callActive = true;
                document.getElementById('mic-btn').classList.add('active');
                document.getElementById('mic-ring').classList.add('active');
                document.getElementById('voice-status').textContent = 'Connected - speak now';
                document.getElementById('voice-hint').textContent = 'Tap the mic to end the call';
                addMessage('Call connected', 'system');
            });

            vapi.on('call-end', () => {
                callActive = false;
                document.getElementById('mic-btn').classList.remove('active');
                document.getElementById('mic-ring').classList.remove('active');
                document.getElementById('voice-status').textContent = 'Call ended';
                document.getElementById('voice-hint').textContent = 'Tap to start a new call';
                addMessage('Call ended', 'system');
            });

            vapi.on('message', (msg) => {
                if (msg.type === 'transcript' && msg.transcriptType === 'final') {
                    const text = msg.transcript.trim();
                    if (!text) return;
                    const lower = text.toLowerCase();
                    if (lower.includes('end call') || lower.includes('ending call')) return;
                    if (msg.role === 'user') addMessage(text, 'user');
                    else if (msg.role === 'assistant') addMessage(text, 'agent');
                }
            });

            vapi.on('error', (e) => {
                console.error('Vapi error:', e);
                if (!callActive) return;
                addMessage('Voice error - please try again', 'system');
                callActive = false;
                document.getElementById('mic-btn').classList.remove('active');
                document.getElementById('mic-ring').classList.remove('active');
                document.getElementById('voice-status').textContent = 'Error occurred';
                document.getElementById('voice-hint').textContent = 'Tap to retry';
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
                document.getElementById('voice-hint').textContent = '';
            }
        }

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
