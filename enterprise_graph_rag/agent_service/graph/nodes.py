from typing import Annotated, Sequence, TypedDict, Literal
import operator
import re
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage,trim_messages
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from agent_service.core.security import SecurityManager
from agent_service.core.config import agent_settings
from agent_service.core.prompts import AGENT_SYSTEM_PROMPT, GRADER_SYSTEM_PROMPT
from agent_service.tools.retrieval import HybridSearchTool
from agent_service.tools.calculator import calculator


try:
    security_manager = SecurityManager.get_instance()
except Exception:
    # Fallback if model not downloaded
    security_manager = None

def scrub_pii(text: str) -> str:
    # Scrub Emails
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '<EMAIL_REDACTED>', text)
    # Scrub Phone Numbers (Generic)
    text = re.sub(r'\+?\d[\d -]{8,12}\d', '<PHONE_REDACTED>', text)
    return text

# --- STATE DEFINITION ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    retry_count: int

# --- MODEL SETUP ---
tools = [HybridSearchTool(), calculator]
llm = ChatOpenAI(model=agent_settings.AGENT_MODEL, temperature=0)

# 1. Agent Model (Binds tools)
agent_model = llm.bind_tools(tools, parallel_tool_calls=True)

# 2. Grader Model (Structured Output)
class GradeDecision(BaseModel):
    """Binary score for relevance check."""
    is_relevant: bool = Field(description="True if the context is relevant to the question.")
    reason: str = Field(description="Brief explanation of why it is relevant or not.")

grader_model = llm.with_structured_output(GradeDecision)

# --- NODES ---

async def guard_node(state: AgentState):
    """
    Security Node: Uses Microsoft Presidio to scrub PII.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, HumanMessage):
        if security_manager:
            clean_text = security_manager.sanitize_input(last_msg.content)
            
            # If changes were made, update the state
            if clean_text != last_msg.content:
                print(f"   🛡️  [Security]: PII Detected & Redacted.")
                # We replace the message in the state so the LLM never sees the PII
                return {"messages": [HumanMessage(content=clean_text, id=last_msg.id)]}
    
    return {} # No changes

async def agent_node(state: AgentState):
    """The Decision Maker."""
    messages = state["messages"]
    
    trimmed_messages = trim_messages(
        messages,
        max_tokens=4000, # Safe limit for "reasoning" context
        strategy="last",
        token_counter=llm, # Uses the model's tokenizer
        include_system=False, # We handle system prompt manually to ensure it's always there
        start_on="human" # Ensure we don't cut in the middle of a tool sequence
    )
    
    # Re-inject System Prompt at the front
    final_messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + trimmed_messages

    response = await agent_model.ainvoke(final_messages)
    return {"messages": [response]}

async def grader_node(state: AgentState):
    """
    Quality Control Node. 
    Checks the LAST ToolMessage to see if the retrieval was useful.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    # Safety Check: If last message isn't from a tool, skip grading
    if not isinstance(last_msg, ToolMessage):
        return {"retry_count": 0}

    # Extract the user's last question for context
    # (Iterate backwards to find the last HumanMessage)
    user_question = next((m.content for m in reversed(messages) if m.type == "human"), "Unknown")
    
    # Invoke Grader LLM (Structured JSON)
    decision: GradeDecision = await grader_model.ainvoke([
        SystemMessage(content=GRADER_SYSTEM_PROMPT),
        HumanMessage(content=f"User Question: {user_question}\n\nRetrieved Context: {last_msg.content}")
    ])

    if not decision.is_relevant:
        current_retries = state.get("retry_count", 0)
        if current_retries < agent_settings.MAX_RETRIES:
            # Feedback to the Agent to try again
            return {
                "messages": [
                    ToolMessage(
                        tool_call_id=last_msg.tool_call_id,
                        content="[System]: The previous search was not relevant. Please try a broader query or different keywords."
                    )
                ],
                "retry_count": current_retries + 1
            }
    
    # If relevant, reset retries
    return {"retry_count": 0}

# --- ROUTING ---

def route_agent(state: AgentState) -> Literal["tools", "end"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return "end"

def route_grader(state: AgentState) -> Literal["agent", "end"]:
    # If the grader incremented retry_count (implying failure), go back to agent
    # We check if the last message was a "System Feedback" ToolMessage injected by the grader
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, ToolMessage) and "[System]: The previous search" in last_msg.content:
        return "agent"
    
    # Otherwise, the tool output was good, let the agent synthesize the answer
    # Wait... usually after tool execution, we go back to Agent to generate the final text.
    # So: Tool -> Grader -> Agent (Generate Answer) -> End
    return "agent"