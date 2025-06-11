from dataclasses import dataclass
from typing import Literal
import streamlit as st

from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryMemory
import streamlit.components.v1 as components

import requests
import uuid

def send_to_n8n(user_input: str):
    url = "https://n8n.1000.school/webhook/7ea84bd5-4ca5-4991-a636-59fb4a8cdc64"
    payload = {
        "user_input": user_input,
        "sessionId": st.session_state.session_id
    }
    try:
        res = requests.post(url, json=payload)
        print("전송된 내용:", payload)
        print("응답 코드:", res.status_code)
        print("응답 원문:", res.text)  # 👈 디버깅용 추가

        # JSON 응답 반환 시도
        return res.json()
    except Exception as e:
        print("JSON 파싱 실패:", e)
        return {"error": f"JSON 파싱 실패: {e}", "raw": res.text}

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
            memory=ConversationSummaryMemory(llm=llm)
        )

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

def on_click_callback():
    with get_openai_callback() as cb:
        human_prompt = st.session_state.human_prompt

        # n8n Webhook으로 입력 전송 및 응답 수신
        n8n_response = send_to_n8n(human_prompt)

        # 응답 출력 처리
        if isinstance(n8n_response, dict):
            if "text" in n8n_response:
                ai_message = n8n_response["text"]
            elif "output" in n8n_response:
                ai_message = n8n_response["output"]  # fallback 처리
            else:
                ai_message = f"(예상치 못한 응답 구조): {n8n_response}"



        # 대화 기록 추가
        st.session_state.history.append(Message("human", human_prompt))
        st.session_state.history.append(Message("ai", ai_message))
        st.session_state.token_count += cb.total_tokens
        st.session_state.human_prompt = ""


load_css()
initialize_session_state()

st.title("일정 관리 도우미 HAMA 🦛")

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
    el => el.innerText === '전송'
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