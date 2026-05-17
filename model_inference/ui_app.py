import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
from code_parser import extract_web_code

st.set_page_config(page_title="OpenVINO Web Designer", layout="wide")

# --- Initialize Session States ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_html" not in st.session_state:
    st.session_state.last_html = ""

# --- Sidebar / Header ---
st.title("🚀 OpenVINO Local Web Coder")
client = OpenAI(base_url="http://localhost:8000/v1", api_key="local-gpu")

# Create two columns: Left for Chat, Right for Preview
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Chat")
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Design a login page with a glassmorphism effect..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # Stream tokens
            stream = client.chat.completions.create(
                model="qwen2.5-coder",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # After streaming is done, check for code to update the preview
            web_code = extract_web_code(full_response)
            if web_code:
                st.session_state.last_html = web_code
                st.rerun() # Refresh to update the preview pane

with col2:
    st.subheader("Live Preview")
    if st.session_state.last_html:
        # Render the HTML in an IFrame
        components.html(st.session_state.last_html, height=600, scrolling=True)
    else:
        st.info("Ask the AI to write HTML/CSS code to see the preview here.")