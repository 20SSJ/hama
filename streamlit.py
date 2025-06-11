from dataclasses import dataclass
from typing import Literal
import streamlit as st
import uuid

from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryMemory
import streamlit.components.v1 as components

import requests

def send_to_n8n(user_input: str):
    url = "https://n8n.1000.school/webhook/7ea84bd5-4ca5-4991-a636-59fb4a8cdc64"
    payload = {
        "user_input": user_input,
        "session_id": st.session_state.get("session_id", "no-session")
    }
    try:
        res = requests.post(url, json=payload)
        st.write("전송된 payload:", payload)
        st.write("n8n 응답 코드:", res.status_code)
        st.write("n8n 응답 내용:", res.text)
        return res.status_code == 200
    except Exception as e:
        st.error(f" n8n 전송 실패: {e}")
        return False


@dataclass
class Message:
    origin: Literal["human", "ai"]
    message: str

def load_css():
    with open("static/styles.css", "r") as f:
        css = f"<style>{f.read()}</style>"
        st.markdown(css, unsafe_allow_html=True)

def initialize_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "token_count" not in st.session_state:
        st.session_state.token_count = 0
    if "conversation" not in st.session_state:
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=st.secrets["open_api_key"],
            model_name="gpt-4o-mini"
        )
        st.session_state.conversation = ConversationChain(
            llm=llm,
            memory=ConversationSummaryMemory(llm=llm),
        )
    if "token_count" not in st.session_state:
        st.session_state.token_count = 0
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

def on_click_callback():
    with get_openai_callback() as cb:
        human_prompt = st.session_state.human_prompt

        # n8n Webhook으로 입력 전송
        send_to_n8n(human_prompt)

        # 기존 LLM 처리
        llm_response = st.session_state.conversation.run(human_prompt)
        st.session_state.history.append(Message("human", human_prompt))
        st.session_state.history.append(Message("ai", llm_response))
        st.session_state.token_count += cb.total_tokens
        st.session_state.human_prompt = ""


load_css()
initialize_session_state()

st.title("일정 생성 도우미 HAMA 🦛")

chat_placeholder = st.container()
prompt_placeholder = st.form("chat-form")
credit_card_placeholder = st.empty()

with chat_placeholder:
    for chat in st.session_state.history:
        div = f"""
<div class="chat-row 
    {'' if chat.origin == 'ai' else 'row-reverse'}">
    <img class="chat-icon" src="app/static/{
        'hippo.png' if chat.origin == 'ai' 
                      else 'user_icon.png'}"
         width=32 height=32>
    <div class="chat-bubble
    {'ai-bubble' if chat.origin == 'ai' else 'human-bubble'}">
        &#8203;{chat.message}
    </div>
</div>
        """
        st.markdown(div, unsafe_allow_html=True)
    
    for _ in range(3):
        st.markdown("")

with prompt_placeholder:
    st.markdown("**hama**")
    cols = st.columns((6, 1))
    cols[0].text_input(
        "hama",
        value="",
        label_visibility="collapsed",
        key="human_prompt",
    )
    cols[1].form_submit_button(
        "전송", 
        type="primary", 
        on_click=on_click_callback, 
    )

components.html("""
<script>
const streamlitDoc = window.parent.document;

const buttons = Array.from(
    streamlitDoc.querySelectorAll('.stButton > button')
);
const submitButton = buttons.find(
    el => el.innerText === 'Submit'
);

streamlitDoc.addEventListener('keydown', function(e) {
    switch (e.key) {
        case 'Enter':
            submitButton.click();
            break;
    }
});
</script>
""", 
    height=0,
    width=0,
)