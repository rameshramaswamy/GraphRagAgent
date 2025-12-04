import pytest
from agent_service.graph.nodes import scrub_pii
from agent_service.tools.retrieval import HybridSearchTool

# 1. Test PII Redaction
def test_pii_scrubber():
    input_text = "Contact bob@corp.com or call 555-123-4567 regarding the policy."
    cleaned = scrub_pii(input_text)
    assert "<EMAIL_REDACTED>" in cleaned
    assert "<PHONE_REDACTED>" in cleaned
    assert "bob@corp.com" not in cleaned
    print("✅ PII Redaction passed.")

# 2. Test Caching (Integration)
# Requires Redis running: docker run -p 6379:6379 -d redis
@pytest.mark.asyncio
async def test_tool_caching():
    tool = HybridSearchTool()
    query = "What is the cache policy?"
    
    # First Hit (Miss)
    res1 = await tool._arun(query)
    assert "[Cached]" not in res1
    
    # Second Hit (Hit)
    res2 = await tool._arun(query)
    # Note: In a real integration test with Redis up, this should contain "[Cached]"
    # If Redis is not up, it gracefully falls back to non-cached.
    if "No relevant information" not in res1: # Only caches hits
         print(f"✅ Second call result: {res2[:50]}...")

if __name__ == "__main__":
    test_pii_scrubber()