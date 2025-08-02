
import os
import sys

# Add project root to the Python path to resolve module import errors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import asyncio
from typing import Any, Dict, List
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
import traceback
import uuid

from agent import business_analyst_agent

APP_NAME = "host_agent_ui"
USER_ID = "streamlit_user"

@st.cache_resource
def get_adk_runner() -> Runner:
    print("🔧 Creating new ADK Runner instance (this should only appear once per session)")
    session_service = InMemorySessionService()
    host_agent = business_analyst_agent
    return Runner(
        agent=host_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

@st.cache_resource
def initialize_adk_session():
    print(f"--- This function is a placeholder and its logic has been moved into run_agent_logic ---")
    return True

async def run_agent_logic(prompt: str, session_id: str) -> Dict[str, Any]:
    try:
        runner = get_adk_runner()

        if 'adk_session_initialized' not in st.session_state:
            try:
                await runner.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id
                )
                print(f"✅ ADK session created: {session_id}")
                st.session_state.adk_session_initialized = True
            except Exception:
                st.session_state.adk_session_initialized = True

        tool_calls = []
        tool_responses = []
        final_response = ""
        pdf_path = None
        excel_path= None

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        tool_calls.append({
                            'name': part.function_call.name,
                            'args': part.function_call.args
                        })
                    elif part.function_response:
                        response_data = part.function_response.response
                        tool_responses.append({
                            'name': part.function_response.name,
                            'response': response_data
                        })

                        # if isinstance(response_data, dict) and 'pdf_path' in response_data:
                        #     pdf_path = response_data['pdf_path']
                        for tool in tool_responses:
                            if tool.get("name") == "save_report" or tool.get("name") == "save_user_manual" or tool.get("name") =="save_usecase_acceptance_criteria":
                                pdf_path = tool.get("response", {}).get("result")
                            elif tool.get("name")=="save_task_chart":
                                excel_path = tool.get("response", {}).get("result")
                                break


            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "".join([p.text for p in event.content.parts if p.text])
                elif event.actions and event.actions.escalate:
                    final_response = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break
            

        return {
            'final_response': final_response,
            'tool_calls': tool_calls,
            'tool_responses': tool_responses,
            'pdf_path': pdf_path,
            'excel_path': excel_path,
            'success': True
        }

    except Exception as e:
        st.error(f"Error running agent: {str(e)}")
        traceback.print_exc()
        return {
            'final_response': f"An error occurred: {str(e)}",
            'tool_calls': [],
            'tool_responses': [],
            'pdf_path': None,
            'success': False
        }

def initialize_session_state():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session-{uuid.uuid4()}"
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'pdf_files' not in st.session_state:
        st.session_state.pdf_files = []

def display_tool_calls(tool_calls: List[Dict[str, Any]]):
    if tool_calls:
        with st.expander(f"🛠️ Tool Calls ({len(tool_calls)})", expanded=False):
            for i, call in enumerate(tool_calls):
                st.code(f"Tool: {call['name']}\nArguments: {call['args']}", language="python")

def display_tool_responses(tool_responses: List[Dict[str, Any]]):
    if tool_responses:
        with st.expander(f"⚡ Tool Responses ({len(tool_responses)})", expanded=False):
            for i, response in enumerate(tool_responses):
                st.write(f"**{response['name']}:**")
                if isinstance(response['response'], dict):
                    st.json(response['response'])
                else:
                    st.text(str(response['response']))

def main():
    st.set_page_config(
        page_title="Business Analyst Agent",
        page_icon="🤖",
        layout="wide"
    )

    get_adk_runner()
    initialize_session_state()

    st.title("🤖 Business Analyst Agent")
    st.markdown("Chat with the Business Analyst Agent that creates project documents based on your input.")

    with st.sidebar:
        st.header("Session Info")
        st.text(f"Session ID: {st.session_state.session_id[:13]}...")
        st.info("🧠 **Agent Memory**: Context is preserved for this session.")

        if st.button("🔄 New Session"):
            st.session_state.clear()
            st.rerun()

        if st.session_state.pdf_files:
            st.header("📄 Generated PDFs")
            for i, pdf_file in enumerate(st.session_state.pdf_files):
                st.download_button(
                    label=f"📥 Download PDF {i+1}",
                    data=open(pdf_file, "rb").read(),
                    file_name=os.path.basename(pdf_file),
                    mime="application/pdf"
                )

    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "tool_calls" in message:
                display_tool_calls(message["tool_calls"])
            if "tool_responses" in message:
                display_tool_responses(message["tool_responses"])

    if prompt := st.chat_input("I'm a Business Analyst. I can create project documents for you!. How can I help you?"):
        st.session_state.conversation_history.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Business Analyst Agent is thinking..."):
                result = asyncio.run(run_agent_logic(prompt, st.session_state.session_id))
                print(result)

            if result['final_response']:
                st.write(result['final_response'])

            display_tool_calls(result['tool_calls'])
            display_tool_responses(result['tool_responses'])

            if result['pdf_path']:
                st.success(f"📄 PDF generated: {os.path.basename(result['pdf_path'])}")
                st.download_button(
                    label="📥 Download PDF",
                    data=open(result['pdf_path'], "rb").read(),
                    file_name=os.path.basename(result['pdf_path']),
                    mime="application/pdf"
                )
                if result['pdf_path'] not in st.session_state.pdf_files:
                    st.session_state.pdf_files.append(result['pdf_path'])
                    
            if result['excel_path']:
                st.success(f"📊 Gantt Chart generated: {os.path.basename(result['excel_path'])}")
                st.download_button(
                    label="📥 Download Gantt Chart",
                    data=open(result['excel_path'], "rb").read(),
                    file_name=os.path.basename(result['excel_path']),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            assistant_message = {
                "role": "assistant",
                "content": result['final_response'],
                "tool_calls": result['tool_calls'],
                "tool_responses": result['tool_responses']
            }
            st.session_state.conversation_history.append(assistant_message)

if __name__ == "__main__":
    main()
