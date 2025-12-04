import asyncio
import hashlib
import json
from typing import Type, Optional, List
import redis
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Import Logic from Phase 1 (Data Foundation)
from knowledge_engine.core.database import GraphDatabaseManager
from knowledge_engine.core.config import settings as knowledge_settings
from llama_index.core import PropertyGraphIndex
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from governance.auth.models import UserIdentity
from governance.policy.access_control import AccessControlPolicy
from knowledge_engine.core.database import GraphDatabaseManager

# Import Agent Settings for Redis/Caching config
from agent_service.core.config import agent_settings

# --- CACHE SETUP ---
# Fail gracefully if Redis is not configured or down
try:
    redis_client = redis.from_url(agent_settings.REDIS_URL)
except Exception:
    redis_client = None

# --- INPUT SCHEMA ---
class HybridSearchInput(BaseModel):
    query: str = Field(
        description="The natural language query to search for. Be specific about entities (e.g., 'Project Apollo', 'Alice Smith')."
    )

# --- TOOL DEFINITION ---
class HybridSearchTool(BaseTool):
    name: str = "knowledge_graph_search"
    description: str = (
        "Useful for answering questions about company policies, employee hierarchy, "
        "project ownership, or specific document details. "
        "Uses a hybrid Vector + Graph approach. "
        "Input should be a clear, specific question."
    )
    args_schema: Type[BaseModel] = HybridSearchInput

    def _run_sync_logic(self, query: str) -> str:
        """
        The core synchronous logic that interacts with Neo4j and LlamaIndex.
        This is separated so we can run it in a thread for async support.
        """
        try:
            # 1. Get Singleton DB Connection
            db_manager = GraphDatabaseManager.get_instance()
            store = db_manager.get_store()
            
            # 2. Reconstruct Index (Lightweight operation, connects to existing store)
            # In a high-load scenario, this index object could be cached as a singleton too.
            index = PropertyGraphIndex.from_existing(
                property_graph_store=store,
                llm=OpenAI(model=knowledge_settings.OPENAI_MODEL, temperature=0),
                embed_model=OpenAIEmbedding(model_name=knowledge_settings.EMBEDDING_MODEL),
            )
            
            # 3. Configure Retriever (Hybrid Mode: Vector + Graph traversal)
            retriever = index.as_retriever(
                include_text=True,
                vector_store_query_mode="hybrid",
                similarity_top_k=5  # Retrieve top 5 most relevant chunks
            )
            
            # 4. Execute Retrieval
            nodes = retriever.retrieve(query)
            
            if not nodes:
                return "No relevant information found in the knowledge base."
                
            # 5. Format Output with Citations
            context_blocks = []
            for i, node in enumerate(nodes, 1):
                # Safe access to metadata
                meta = node.metadata or {}
                source = meta.get('file_name', 'Unknown Source')
                page = meta.get('page_label', 'N/A')
                score = node.score if node.score else 0.0
                
                content = node.get_content().strip()
                
                # Format: [1] Source: Policy.pdf (Page 2) - Content...
                block = f"[{i}] Source: {source} (Page {page})\n{content}"
                context_blocks.append(block)
            
            return "\n\n".join(context_blocks)

        except Exception as e:
            # Return error as string so the LLM knows what happened
            return f"Error querying knowledge base: {str(e)}"

    async def _arun(self, query: str, config: Optional[dict] = None) -> str:
        """
        Async search with RLS.
        """
        # 1. Extract User Identity from LangGraph Config
        user_identity = None
        if config and "configurable" in config:
            user_identity = config["configurable"].get("user_identity")
            
        if not user_identity:
            # Fail closed if no identity is present in a secured env
            return "Error: security_context_missing"

        # 2. Get RLS Policy
        rls = AccessControlPolicy.get_rls_filters(user_identity)
        
        # 3. Execute Search (Modified Logic)
        return await self._execute_secure_search(query, rls)

    async def _execute_secure_search(self, query: str, rls: dict) -> str:
        # ... Init DB ...
        db_manager = GraphDatabaseManager.get_instance()

        cypher_query = f"""
            CALL db.index.fulltext.queryNodes("entity_name_index", $query) YIELD node, score
            WITH node, score
            MATCH (node)-[:MENTIONS]->(d:Document)
            WHERE {rls['cypher']}  // <--- RLS APPLIED HERE
            RETURN node.name as entity, d.file_name as source, node.text as text
            LIMIT 5
        """
        
        # Merge params
        params = {"query": query, **rls['params']}
        
        results = db_manager.run_cypher(cypher_query, params)
        
        if not results:
            return "No relevant information found (or access denied)."
            
        return "\n".join([f"Entity: {r['entity']} (Source: {r['source']})" for r in results])

    def _run(self, query: str) -> str:
        return "Synchronous execution not supported in Secure Mode."