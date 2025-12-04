from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import AsyncConnectionPool

from agent_service.core.config import agent_settings
from agent_service.graph.nodes import (
    AgentState, 
    agent_node, 
    grader_node, 
    guard_node ,
    route_agent, 
    route_grader, 
    tools
)

# Global Pool for Async Persistence
_pool = None

def get_async_pool():
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=agent_settings.POSTGRES_URI,
            max_size=20,
            kwargs={"autocommit": True}
        )
    return _pool

def build_graph():
    """
    Constructs the StateGraph. 
    Note: We return the graph builder. The caller should compile it with the checkpointer.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("guard", guard_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("grader", grader_node)

    # Add Edges
    workflow.add_edge(START, "guard")
    workflow.add_edge("guard", "agent") 

    # 1. Agent decides: Call Tool or End?
    workflow.add_conditional_edges(
        "agent",
        route_agent,
        {
            "tools": "tools",
            "end": END
        }
    )

    # 2. Tool executed -> Check Quality
    workflow.add_edge("tools", "grader")

    # 3. Grader decides: Good? (Go to Agent to answer) OR Bad? (Go to Agent to retry)
    # Note: In both cases we go to 'agent', but the State (messages) differs.
    # The 'route_grader' logic is actually implicit here because we always go back to agent
    # unless we want to force a loop break. 
    # But explicitly:
    workflow.add_edge("grader", "agent")

    return workflow

async def get_compiled_graph():
    """Async factory to get the compiled app with DB persistence."""
    pool = get_async_pool()
    checkpointer = PostgresSaver(pool)
    await checkpointer.setup()
    
    workflow = build_graph()
    return workflow.compile(checkpointer=checkpointer)