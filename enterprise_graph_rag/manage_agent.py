import asyncio
import sys
from langchain_core.messages import HumanMessage
from agent_service.graph.workflow import get_compiled_graph

# Fix for Windows/Jupyter
import nest_asyncio
nest_asyncio.apply()

async def chat_session(thread_id: str):
    print(f"\n--- Enterprise Agent (Thread: {thread_id}) ---")
    app = await get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}

    print("✅ Ready. Type 'q' to quit.")

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["q", "quit"]:
            break
        
        input_msg = {"messages": [HumanMessage(content=user_input)], "retry_count": 0}
        
        print("AI: ", end="", flush=True)
        
        # Optimization: Use astream_events for token-level streaming
        async for event in app.astream_events(input_msg, config=config, version="v1"):
            kind = event["event"]
            
            # 1. Stream Tokens from the Agent (LLM)
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    print(content, end="", flush=True)
            
            # 2. Visual Feedback for Tools
            elif kind == "on_tool_start":
                print(f"\n   ⚙️  [Tool Call]: {event['name']}...", end="", flush=True)
            
            elif kind == "on_tool_end":
                print(f" (Done)\nAI: ", end="", flush=True) # Resume AI line

        print("") # Newline at end of turn

if __name__ == "__main__":
    t_id = "prod-optimized-session"
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(chat_session(t_id))