import streamlit as st
import requests
import json

st.title("💬 Local LLM Chat (Ollama)")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("You:", key="input")

if user_input:
    st.session_state.chat_history.append(("🧑", user_input))

    with st.spinner("Thinking..."):
        reply = ""
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "TinyLlama", "prompt": user_input},
            stream=True
        )

        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    reply += data.get("response", "")
                except json.JSONDecodeError:
                    continue

    st.session_state.chat_history.append(("🤖", reply))

for role, msg in st.session_state.chat_history:
    st.markdown(f"**{role}**: {msg}")
