import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import streamlit as st

from app.api_client import create_conversation, send_message
from app.config import API_BASE_URL

import logging
from pythonjsonlogger import jsonlogger

# --- CONFIGURATION LOGGING JSON ---
def setup_frontend_logging():
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(message)s'
    )
    # On récupère le logger root
    logger = logging.getLogger()
    
    # On nettoie les handlers existants
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # On configure la sortie standard avec notre formateur JSON
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)

# Initialisation immédiate
setup_frontend_logging()

# --- Page config (must be first Streamlit call) ---
st.set_page_config(
    page_title="RAG Sample — Assistant IA",
    page_icon="💬",
    layout="centered",
)

# --- Brand CSS: Space Grotesk font + chat bubble colors ---
_USER_BUBBLE_SELECTOR = "[data-testid=\"stChatMessage\"]:has([data-testid=\"chatAvatarIcon-user\"]) [data-testid=\"stChatMessageContent\"]"  # noqa: E501
_ASST_BUBBLE_SELECTOR = "[data-testid=\"stChatMessage\"]:has([data-testid=\"chatAvatarIcon-assistant\"]) [data-testid=\"stChatMessageContent\"]"  # noqa: E501
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li, .stMarkdown p {{
        font-family: 'Space Grotesk', sans-serif !important;
    }}

    /* User bubble */
    {_USER_BUBBLE_SELECTOR} {{
        background-color: #2098D1 !important;
        color: #FFFFFF !important;
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }}

    /* Assistant bubble */
    {_ASST_BUBBLE_SELECTOR} {{
        background-color: #F0F4F8 !important;
        color: #1A1A1A !important;
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
st.markdown(
    """
    <div style="text-align:center; padding: 1.5rem 0 0.5rem 0;">
        <span style="font-family:'Space Grotesk',sans-serif; font-weight:700;
                     font-size:2rem; color:#1A1A1A; letter-spacing:0.05em;">
            RAG Sample
        </span><br/>
        <span style="font-family:'Space Grotesk',sans-serif; font-weight:400;
                     font-size:1rem; color:#2098D1;">
            Assistant IA
        </span>
    </div>
    <hr style="border:none; border-top:2px solid #2098D1; margin: 0.5rem 0 1.5rem 0;">
    """,
    unsafe_allow_html=True,
)

# --- Session initialisation ---
if "conversation_id" not in st.session_state:
    try:
        conv_id = create_conversation(API_BASE_URL)
        st.session_state.conversation_id = conv_id
        st.session_state.messages = []
        # LOG : Session démarrée
        logging.info("Frontend: New session initialized", extra={"conversation_id": conv_id})

    except Exception:
        logging.error("Frontend: Critical failure at session init")
        st.error("Impossible de joindre l'API.")
        st.stop()

# --- Render conversation history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📎 Sources ({len(msg['sources'])})"):
                for chunk_id in msg["sources"]:
                    st.caption(f"Chunk : {chunk_id}")

# --- Handle new user input ---
if prompt := st.chat_input("Posez votre question…"):
    # LOG : Message envoyé
    logging.info("Frontend: User submitted a prompt", extra={
        "conversation_id": st.session_state.conversation_id
    })

    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        content: str = ""
        sources: list[str] = []
        with st.spinner("Génération en cours…"):
            try:
                response = send_message(
                    API_BASE_URL,
                    st.session_state.conversation_id,
                    prompt,
                )
                content = response["content"] or "Aucune réponse reçue."
                sources = response.get("sources", [])
            except httpx.HTTPStatusError as e:
                st.error(f"Erreur API : {e.response.status_code}")
                st.stop()
            except Exception:
                st.error("Impossible de joindre l'API.")
                st.stop()

        st.markdown(content)
        if sources:
            with st.expander(f"📎 Sources ({len(sources)})"):
                for chunk_id in sources:
                    st.caption(f"Chunk : {chunk_id}")

    st.session_state.messages.append(
        {"role": "assistant", "content": content, "sources": sources}
    )
