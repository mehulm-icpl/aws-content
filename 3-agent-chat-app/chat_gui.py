import boto3
import json
import gradio as gr
import uuid
import datetime
from boto3.session import Session
from botocore.exceptions import ClientError
from botocore.config import Config

def retrieve_parameter_value(ssm_client, parameter_name: str) -> str:
    """Get parameter from SSM parameter store."""
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as error:
        print(f"Error retrieving parameter {parameter_name}: {error}")
        raise error

# ── AWS clients ────────────────────────────────────────────────────────────────
boto_session   = Session()
region         = boto_session.region_name
ssm_client     = boto3.client('ssm', region_name=region)

# Extended timeout for browser operations (may take 1-3 minutes)
client_config = Config(
    read_timeout=600,
    connect_timeout=60,
    retries={"max_attempts": 2}
)
agentcore_client = boto3.client('bedrock-agentcore', region_name=region, config=client_config)

# ── SSM parameters ─────────────────────────────────────────────────────────────
agent_arn = retrieve_parameter_value(ssm_client, "agent_arn")

try:
    introductory_message = retrieve_parameter_value(ssm_client, "introductory_message")
    print(f"[Info] Introductory message found: {introductory_message[:50]}...")
except ClientError:
    introductory_message = "Hello! I am your AI assistant. How can I help you today?"
    print("[Info] Introductory message parameter not found - using default")

try:
    account_email = retrieve_parameter_value(ssm_client, "account_email")
    print(f"[Info] Account email found: {account_email}")
except ClientError:
    account_email = ""
    print("[Info] Account email parameter not found")

try:
    account_message = retrieve_parameter_value(ssm_client, "account_message")
    print(f"[Info] Account message found: {account_message[:50]}...")
except ClientError:
    account_message = "Hello, I'd like to schedule a GenAI discovery meeting."
    print("[Info] Account message parameter not found")

try:
    logo_path = retrieve_parameter_value(ssm_client, "logo_path")
    print(f"[Info] Logo parameter found: {logo_path}")
except ClientError:
    logo_path = ""
    print("[Info] Logo parameter not found")

# voting_url is set/cleared by the event organizer via the admin dashboard
# Empty = voting not open yet. Set = voting is open.
try:
    _initial_voting_url = retrieve_parameter_value(ssm_client, "voting_url")
    print(f"[Info] Voting URL found: {_initial_voting_url}")
except ClientError:
    _initial_voting_url = ""
    print("[Info] Voting URL not set")

# ── Session management ─────────────────────────────────────────────────────────
chat_sessions      = {}
initial_history    = [{"role": "assistant", "content": introductory_message}]

def generate_session_id():
    return str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')[:5]

def get_session_title(first_message):
    return first_message[:30] + "..." if len(first_message) > 30 else first_message

def get_session_choices():
    if not chat_sessions:
        return []
    choices = []
    for sid, data in sorted(chat_sessions.items(), key=lambda x: x[1]["created"], reverse=True):
        choices.append(f"{data['created'].strftime('%H:%M')} - {data['title']}")
    return choices

def start_new_chat(session_state):
    new_id = generate_session_id()
    print(f"[Chat] New session: {new_id}")
    return initial_history, "", gr.Radio(choices=get_session_choices(), value=None), new_id

def load_chat_session(session_selection, session_state):
    if not session_selection or session_selection == "No previous chats":
        return initial_history, "", session_state
    try:
        selected_title = session_selection.split(" - ", 1)[1]
        for sid, data in chat_sessions.items():
            if data["title"] == selected_title:
                history = data["history"].copy()
                if not history or history[0].get("content") != introductory_message:
                    history.insert(0, {"role": "assistant", "content": introductory_message})
                return history, "", sid
    except:
        pass
    return initial_history, "", session_state

def save_chat_message(session_id, message, response):
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "history": [],
            "title": get_session_title(message),
            "created": datetime.datetime.now()
        }
    chat_sessions[session_id]["history"].extend([
        {"role": "user",      "content": message},
        {"role": "assistant", "content": response}
    ])

def chat_with_agent_simple(message, history, session_state):
    try:
        print(f"\n[Chat] Sending message | Session: {session_state}")
        boto3_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_state,
            payload=json.dumps({"prompt": message, "history": history})
        )
        accumulated_bytes = b""
        event_count = 0
        for event in boto3_response.get("response", []):
            event_count += 1
            accumulated_bytes += event
        try:
            event_data = accumulated_bytes.decode('utf-8')
        except UnicodeDecodeError:
            event_data = accumulated_bytes.decode('utf-8', errors='replace')
            print("[Warning] UTF-8 decoding issue")
        try:
            data = json.loads(event_data)
            if isinstance(data, dict) and 'content' in data:
                full_response = "".join(item['text'] for item in data['content'])
            else:
                full_response = str(data)
        except json.JSONDecodeError:
            full_response = event_data
        print(f"[Chat] Processed {event_count} events")
        if full_response:
            full_response = full_response.replace('\\n', '\n')
            save_chat_message(session_state, message, full_response.strip())
            return full_response.strip()
        return "No response received from agent"
    except Exception as e:
        print(f"[Chat] Error: {e}")
        return f"Error connecting to agent: {str(e)}"

# ── RTL CSS ────────────────────────────────────────────────────────────────────
RTL_CSS = """<style id="rtl-style">
/* RTL layout — but text direction is auto-detected per paragraph */
.gradio-container { direction: rtl; }
.message-wrap, .message { direction: rtl; unicode-bidi: plaintext; text-align: start; }
.chatbot .message-bubble-border, .chatbot .message-bubble { direction: rtl; unicode-bidi: plaintext; text-align: start; }
textarea, input[type="text"] { direction: rtl; unicode-bidi: plaintext; text-align: start; }
.md, .markdown-text, .prose { unicode-bidi: plaintext; text-align: start; }
.md p, .prose p, .md li, .prose li { unicode-bidi: plaintext; text-align: start; direction: auto; }
.md ul, .md ol, .prose ul, .prose ol { padding-right: 1.5em; padding-left: 0; }
.app-header { direction: ltr; }
.mvp-footer { direction: rtl; }
.chat-history { direction: rtl; text-align: start; }
.examples-row button { direction: rtl; text-align: start; }
.submit-button { margin-left: 0 !important; margin-right: 8px !important; }
.input-container { direction: rtl; }
</style>"""
REMOVE_RTL_CSS = """<style id="rtl-style"></style>"""

def toggle_rtl(current_label):
    if "Off" in current_label:
        return RTL_CSS, "🔤 RTL On"
    return REMOVE_RTL_CSS, "🔤 RTL Off"

# ── Contact link ───────────────────────────────────────────────────────────────
contact_value = account_email.strip()
if contact_value.startswith("http://") or contact_value.startswith("https://"):
    contact_link   = contact_value
    link_attrs     = 'target="_blank" rel="noopener noreferrer"'
elif contact_value:
    contact_link   = f"mailto:{contact_value}?subject=GenAI Discovery Meeting&body={account_message}"
    link_attrs     = ''
else:
    contact_link   = ""
    link_attrs     = ""


# ── CSS — loaded from styles.css (keeps this file clean and readable) ──────────
with open('styles.css') as f:
    custom_css = f.read()


# ── App name & description ─────────────────────────────────────────────────────
app_name        = retrieve_parameter_value(ssm_client, "application_name")
app_description = retrieve_parameter_value(ssm_client, "application_description")
app_examples    = [[item.strip()] for item in retrieve_parameter_value(ssm_client, "application_examples").split(',')]

# ── Build header HTML ──────────────────────────────────────────────────────────
aws_logo_html = '<img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" alt="AWS" style="height:28px;width:auto;filter:brightness(0)invert(1)">'
partner_logo_html = f'<span style="background:#fff;border-radius:6px;padding:4px 10px;display:inline-flex;align-items:center"><img src="{logo_path}" alt="Partner" style="height:32px;min-width:32px;width:auto;max-width:120px;object-fit:contain;display:block"></span>' if logo_path else ''
divider_html  = '<div class="header-divider"></div>' if logo_path else ''

header_html = f"""
<div class="app-header">
    <button class="sidebar-toggle" onclick="
        var s = document.querySelector('.sidebar-panel');
        if(s) s.classList.toggle('open');
    ">☰</button>
    {aws_logo_html}
    {divider_html}
    {partner_logo_html}
    <div class="header-title">{app_name}</div>
    <div class="header-badge">Powered by AWS AgentCore</div>
</div>
"""

# ── Build footer HTML ──────────────────────────────────────────────────────────
if contact_link:
    lets_talk_html = f'<a href="{contact_link}" {link_attrs}>Let\'s Talk →</a>'
else:
    lets_talk_html = ''

footer_html = f"""
<div class="mvp-footer">
    <p><span class="footer-text" style="color:rgba(255,255,255,0.9)!important">🚀 Built in 3 hours. Discover what GenAI can do for your team.</span> {lets_talk_html}</p>
</div>
"""

# ── Gradio layout ──────────────────────────────────────────────────────────────
with gr.Blocks(title=app_name) as demo:

    # Per-tab session state — each browser tab gets its own session ID
    session_state = gr.State(value=generate_session_id())

    # Header
    gr.HTML(header_html)

    # Main layout
    with gr.Row():

        # ── Sidebar ───────────────────────────────────────────────────────────
        with gr.Column(scale=1, elem_classes=["sidebar-panel"]):

            gr.HTML('<div class="sidebar-section-label">Conversations</div>')

            new_chat_btn = gr.Button(
                "＋  New Chat",
                elem_classes=["new-chat-btn"],
                size="sm"
            )

            rtl_css_block = gr.HTML(value="", visible=True)
            rtl_btn = gr.Button(
                "🔤 RTL Off",
                elem_classes=["rtl-btn"],
                size="sm",
                variant="secondary"
            )
            rtl_btn.click(fn=toggle_rtl, inputs=[rtl_btn], outputs=[rtl_css_block, rtl_btn])

            # ── Vote panel ────────────────────────────────────────────────────
            # A gr.HTML component that starts as a plain decorative panel.
            # A hidden gr.Button triggers an SSM check on click.
            # When voting_url is set: panel becomes a real <a> link → opens in new tab.
            # When voting_url is cleared: reverts to plain panel.
            VOTE_BLANK = '<div class="vote-panel">&nbsp;</div>'

            def make_vote_link(url):
                # Real <a> tag — Gradio renders this, browser handles navigation
                return (f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                        f'class="vote-panel active" '
                        f'style="display:block;text-align:center;text-decoration:none;">'
                        f'🗳&nbsp;&nbsp;Vote Now</a>')

            vote_html    = gr.HTML(value=VOTE_BLANK)
            vote_trigger = gr.Button(
                "·",  # single dot — nearly invisible, sits below the HTML panel
                elem_classes=["vote-trigger"],
                size="sm"
            )

            def handle_vote_click():
                try:
                    url = retrieve_parameter_value(ssm_client, "voting_url").strip()
                except ClientError:
                    url = ""
                return make_vote_link(url) if url else VOTE_BLANK

            vote_trigger.click(fn=handle_vote_click, inputs=[], outputs=[vote_html])

            session_list = gr.Radio(
                choices=[],
                value=None,
                label="Previous Chats",
                interactive=True,
                elem_classes=["chat-history-list"]
            )

        # ── Chat area ─────────────────────────────────────────────────────────
        with gr.Column(scale=4, elem_classes=["chat-main"]):

            chat_interface = gr.ChatInterface(
                fn=chat_with_agent_simple,
                # title and description removed — shown in the fixed header instead
                examples=app_examples,
                additional_inputs=[session_state],
                concurrency_limit=10,
                autoscroll=True,
                chatbot=gr.Chatbot(
                    height=500,
                    render_markdown=True,
                    value=initial_history,
                    show_label=False,
                    elem_classes=["main-chatbot"],
                    avatar_images=('./human.png', './bot.png'),
                )
            )

    # Footer
    gr.HTML(footer_html)

    # ── Event wiring ──────────────────────────────────────────────────────────
    new_chat_btn.click(
        fn=start_new_chat,
        inputs=[session_state],
        outputs=[chat_interface.chatbot, chat_interface.textbox, session_list, session_state]
    )
    session_list.change(
        fn=load_chat_session,
        inputs=[session_list, session_state],
        outputs=[chat_interface.chatbot, chat_interface.textbox, session_state]
    )

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Bedrock Agent Chat Interface")
    print("=" * 60)
    print(f"Region:    {region}")
    print(f"Agent ARN: {agent_arn}")
    print(f"Server:    http://0.0.0.0:8084")
    print("=" * 60)
    print("\nChat interface ready. Open your browser to start chatting.")
    print("* AppURL is in the Workshop Studio event outputs")
    print("* Stop with Ctrl+C")
    demo.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=8084,
        css=custom_css
    )
