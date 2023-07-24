import streamlit as st
import yaml
import os
import openai

from pg_qna import qna_llm

# Read config yaml file
with open('./streamlit_app/config.yml', 'r') as file:
    config = yaml.safe_load(file)
#print(config)
title = config['streamlit']['title']
avatar = {
    'user': None,
    'assistant': config['streamlit']['avatar']
}

# Set page config
st.set_page_config(
    page_title=config['streamlit']['tab_title'], 
    page_icon=config['streamlit']['page_icon'], 
    )

# Set sidebar
st.sidebar.image(config['streamlit']['logo'], width=50)
st.sidebar.title("About")
st.sidebar.info(config['streamlit']['about'])

# Set logo
#st.image(config['streamlit']['logo'], width=50)

# Set page title
st.title(title)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [] 
    st.session_state.messages.append({
        "role": "assistant", 
        "content": config['streamlit']['assistant_intro_message']
        })

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=avatar[message["role"]]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Send a message"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Get bot response    
    response = qna_llm(prompt)
    with st.chat_message("assistant", avatar=config['streamlit']['avatar']):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})


    
