import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI

# 1. Test Pruning Logic (Unit)
def test_message_pruning():
    llm = ChatOpenAI(model="gpt-4o")
    # Create 20 dummy messages
    messages = [HumanMessage(content=f"Msg {i}") for i in range(20)]
    
    trimmed = trim_messages(
        messages,
        max_tokens=50, # Very small limit
        strategy="last",
        token_counter=llm,
        include_system=False,
        start_on="human"
    )
    
    # Should only keep the last few
    assert len(trimmed) < 20
    assert trimmed[-1].content == "Msg 19"
    print("✅ Context pruning works.")

# 2. Test Parallel Tool Execution (Integration - Mocked DB)
# For this, we observe the logs in manage_agent.py.
# Query: "Who manages Project Apollo and what is 50 * 20?"
# Expected: "on_tool_start" for search AND calculator should appear close together.