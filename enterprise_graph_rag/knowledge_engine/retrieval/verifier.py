import logging
from llama_index.core import PropertyGraphIndex
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from knowledge_engine.core.config import settings
from knowledge_engine.core.database import GraphDatabaseManager

logger = logging.getLogger(__name__)

class GraphVerifier:
    def __init__(self):
        self.db_manager = GraphDatabaseManager.get_instance()
        self.graph_store = self.db_manager.get_store()
        
        # Re-attach to existing index
        self.index = PropertyGraphIndex.from_existing(
            property_graph_store=self.graph_store,
            llm=OpenAI(model=settings.OPENAI_MODEL),
            embed_model=OpenAIEmbedding(model_name=settings.EMBEDDING_MODEL),
        )

    def verify_retrieval(self, query: str):
        """
        Runs a hybrid retrieval and prints the retrieved context 
        and the raw Neo4j sub-graph structure.
        """
        print(f"\n--- Verifying Query: '{query}' ---")
        
        # 1. Standard Retrieval (What the LLM sees)
        retriever = self.index.as_retriever(
            include_text=True,
            vector_store_query_mode="hybrid",
            similarity_top_k=2
        )
        nodes = retriever.retrieve(query)
        
        print(f"\n[Hybrid Search Results]: Found {len(nodes)} context nodes.")
        for i, node in enumerate(nodes):
            print(f"  {i+1}. {node.get_content()[:100]}...")

        # 2. Structural Verification (What is in the DB)
        # We manually check if specific entities from the query exist in relationships
        print("\n[Database Inspection]: checking for related triples...")
        
        cypher_query = """
        MATCH (n)-[r]->(m)
        WHERE toLower(n.name) CONTAINS toLower($keyword) 
           OR toLower(m.name) CONTAINS toLower($keyword)
        RETURN n.name, type(r), m.name LIMIT 5
        """
        
        # Extract a simple keyword from query for validation (naive approach for testbed)
        # In a real app, we'd use entity extraction on the query first.
        keywords = query.replace("?", "").split()
        keyword = keywords[-1] if keywords else "" # Pick last word as heuristic
        
        results = self.db_manager.run_cypher(cypher_query, {"keyword": keyword})
        
        if results:
            print(f"✅ Found graph paths relating to '{keyword}':")
            for record in results:
                print(f"   ({record['n.name']}) -[{record['type(r)']}]-> ({record['m.name']})")
        else:
            print(f"⚠️ No direct graph paths found for keyword '{keyword}'. Context relies on Vector Search.")