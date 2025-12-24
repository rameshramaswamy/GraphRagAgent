

# Enterprise Graph RAG Agent

This directory contains the **Enterprise-Grade implementation** of the Graph Retrieval-Augmented Generation (GraphRAG) Agent. Unlike standard RAG systems that rely solely on vector embeddings, this agent leverages **Knowledge Graphs** to provide structured, multi-hop reasoning and superior context retrieval for complex enterprise datasets.

##  Overview

The `enterprise_graph_rag` agent is designed to bridge the gap between unstructured document data and structured relational knowledge. It uses a combination of Graph Databases (e.g., Neo4j/Memgraph) and Vector Stores to perform "Hybrid Search," ensuring that queries requiring global context or relationship-specific answers are handled with high precision.

### Key Features
- **Multi-Hop Reasoning**: Traverses relationships between entities to answer complex questions that vector-only RAG often misses.
- **Entity Extraction & Linking**: Automated pipeline to extract entities and relationships from raw text and link them into a persistent graph schema.
- **Hybrid Retrieval**: Seamlessly combines vector similarity search with Cypher-based graph queries.
- **Scalable Architecture**: Optimized for large-scale enterprise documents with support for parallel processing and persistent storage.
- **Traceability**: Every answer includes the graph nodes and relationships used for generation, improving auditability and reducing hallucinations.

---

##  Architecture

The system follows a standard Enterprise Graph RAG pipeline:
1. **Ingestion**: Documents are parsed and chunks are sent to an LLM for entity/relationship extraction.
2. **Indexing**: Extracted data is stored in a Graph Database (Nodes & Edges) and a Vector Database (Embeddings).
3. **Query Expansion**: User queries are analyzed to identify key entities and potential graph traversal paths.
4. **Retrieval**: The system fetches relevant sub-graphs and vector chunks.
5. **Generation**: An LLM synthesizes the final response using the enriched context.

---

##  Installation

### Prerequisites
- Python 3.10+
- A running instance of a Graph Database (e.g., **Neo4j**)
- Access to an LLM provider (OpenAI, Anthropic, or local via Ollama)

### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/rameshramaswamy/GraphRagAgent.git
   cd GraphRagAgent/enterprise_graph_rag
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

##  Configuration

Create a `.env` file in this directory with the following variables:

```env
# LLM Configuration
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4-turbo

# Graph Database (Neo4j Example)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Vector Store
VECTOR_DB_TYPE=pinecone  # or weaviate, faiss, etc.
```

---

##  Usage

### 1. Data Ingestion
To build the knowledge graph from your documents, run:
```bash
python ingest.py --data_path ./data/documents/
```

### 2. Running the Agent
Start the agent to begin querying:
```bash
python main.py
```

### 3. Example Query
```python
from agent import GraphRAGAgent

agent = GraphRAGAgent()
response = agent.query("What are the cross-departmental impacts of Project X on the logistics supply chain?")
print(response)
```

---

##  Project Structure

- `/core`: Core logic for graph traversal and RAG orchestration.
- `/extractors`: LLM-based modules for entity and relationship extraction.
- `/schema`: Definitions for graph nodes, relationships, and metadata.
- `/utils`: Helper functions for document parsing and embedding generation.

---

##  Contributing
Contributions are welcome! Please follow the standard pull request workflow and ensure all tests pass before submitting.

