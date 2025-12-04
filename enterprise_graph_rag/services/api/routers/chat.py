import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

# Import Phase 2 Logic
from agent_service.graph.workflow import get_compiled_graph
from services.api.schemas import ChatRequest
from fastapi import Request
from services.api.limiter import limiter
from fastapi import Security
from governance.auth.oidc import authenticator
from governance.auth.models import UserIdentity

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/stream")
@limiter.limit("10/minute")
async def stream_chat(request: ChatRequest, user: UserIdentity = Security(authenticator.verify_token)):
    """
    Streams the agent's reasoning and response using Server-Sent Events (SSE).
    """
    try:
        # Get the Graph
        app = await get_compiled_graph()
        
        # Prepare Input
        input_msg = {
            "messages": [HumanMessage(content=request.message)], 
            "retry_count": 0
        }
        config = {"configurable": {"thread_id": request.thread_id, "user_identity": user }}

        async def event_generator():
            # Use the optimized 'astream_events' from Phase 2
            async for event in app.astream_events(input_msg, config=config, version="v1"):
                kind = event["event"]
                
                # 1. Stream Tokens
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        # SSE Format: data: <content>\n\n
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                
                # 2. Stream Tool Usage (Optional Metadata)
                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"
            
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))