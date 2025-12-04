from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class OutputGuard(BaseModel):
    is_safe: bool = Field(description="False if response contains PII, toxicity, or hallucinates.")
    reason: str

class OutputGuardrail:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(OutputGuard)

    async def validate_response(self, question: str, response: str) -> str:
        """
        Checks the agent's response before sending to user.
        """
        check = await self.llm.ainvoke(f"""
        Analyze this AI response for safety.
        
        Question: {question}
        Response: {response}
        
        Violations to check:
        1. PII (Emails, Phone Numbers)
        2. Toxic/Harmful content
        3. Clear Hallucinations (claiming to know internal secrets not in evidence)
        
        Result:
        """)
        
        if not check.is_safe:
            return f"[Security Blocked]: The response was flagged: {check.reason}"
        
        return response