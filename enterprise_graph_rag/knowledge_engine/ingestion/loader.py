import os
import hashlib
import asyncio
from typing import List, Set
from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex, Settings as LlamaSettings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Import Schema-guided extractors
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor

from knowledge_engine.core.config import settings
from knowledge_engine.core.database import GraphDatabaseManager
from knowledge_engine.core.logging import logger
from knowledge_engine.core.exceptions import IngestionError

class IngestionPipeline:
    def __init__(self):
        self.db_manager = GraphDatabaseManager.get_instance()
        
        # Configure LLMs with timeouts
        self.llm = OpenAI(
            model=settings.OPENAI_MODEL, 
            temperature=0, 
            request_timeout=60.0
        )
        self.embed_model = OpenAIEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )
        # Optimization: Configurable Chunking
        LlamaSettings.node_parser = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

    def _compute_file_hash(self, file_path: str) -> str:
        """Calculates SHA256 hash of a file to detect changes."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_processed_hashes(self) -> Set[str]:
        """Fetch list of already ingested file hashes from Neo4j."""
        query = "MATCH (d:Document) RETURN d.file_hash as hash"
        results = self.db_manager.run_cypher(query)
        return {r['hash'] for r in results if r.get('hash')}
    
    async def process_directory_async(self, input_dir: str) -> dict:
        if not os.path.exists(input_dir):
            raise IngestionError(f"Directory {input_dir} not found.")

        logger.info("starting_smart_ingestion", directory=input_dir)
        
        # 1. Delta Load Logic
        processed_hashes = self._get_processed_hashes()
        logger.info("found_existing_records", count=len(processed_hashes))

        # Filter files
        files_to_process = []
        skipped_count = 0
        
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.startswith("."): continue # Skip hidden
                file_path = os.path.join(root, file)
                file_hash = self._compute_file_hash(file_path)
                
                if file_hash in processed_hashes:
                    skipped_count += 1
                else:
                    files_to_process.append((file_path, file_hash))

        if not files_to_process:
            logger.info("no_new_files_detected")
            return {"status": "skipped", "processed": 0, "skipped": skipped_count}

        logger.info("processing_new_files", count=len(files_to_process))

        # 2. Setup Ontology-Guided Extractor
        # This forces the LLM to only look for specific things, saving tokens and improving graph quality.
        kg_extractor = SimpleLLMPathExtractor(
            llm=LlamaSettings.llm,
            extract_prompt_kwargs={
                "allowed_entity_types": settings.ALLOWED_ENTITY_TYPES,
                "allowed_relation_types": settings.ALLOWED_RELATION_TYPES
            },
            num_workers=4,
            max_paths_per_chunk=10
        )

        store = self.db_manager.get_store()

        # 3. Process Batch
        try:
            # Load only new files
            paths = [fp for fp, _ in files_to_process]
            reader = SimpleDirectoryReader(input_files=paths, filename_as_id=True)
            documents = reader.load_data()

            # Inject Metadata (Hash) into Document objects
            # We map filename to hash for injection
            hash_map = {fp: fh for fp, fh in files_to_process}
            
            for doc in documents:
                f_path = doc.metadata.get('file_path')
                if f_path and f_path in hash_map:
                    doc.metadata['file_hash'] = hash_map[f_path]
                    # Also explicitly tag the document type
                    doc.metadata['entity_type'] = 'Document'

            logger.info("extracting_graph_with_schema")
            
            # Use run_in_executor to keep the main loop free
            await asyncio.to_thread(
                PropertyGraphIndex.from_documents,
                documents,
                property_graph_store=store,
                kg_extractors=[kg_extractor], # <--- APPLIED SCHEMA HERE
                show_progress=True
            )
            
            # 4. Post-Process: Link Source Documents
            # The PropertyGraphIndex creates chunks, but we want a clean Document Node too.
            # We run a quick Cypher to ensure the 'Document' node exists and is linked.
            self._link_chunks_to_documents()

            return {"status": "success", "processed": len(files_to_process), "skipped": skipped_count}

        except Exception as e:
            logger.error("ingestion_failed", error=str(e), exc_info=True)
            raise IngestionError(f"Smart processing failed: {str(e)}")

    def _link_chunks_to_documents(self):
        """
        Optimization: Explicitly link chunks back to a parent 'Document' node 
        for better citation/filtering.
        """
        logger.info("linking_metadata_nodes")
        # Cypher to ensure (:Document) nodes exist based on properties stored in Chunks
        query = """
        MATCH (c:Chunk)
        WHERE c.file_hash IS NOT NULL
        MERGE (d:Document {file_hash: c.file_hash})
        ON CREATE SET 
            d.file_name = c.file_name, 
            d.created_at = timestamp()
        MERGE (c)-[:BELONGS_TO]->(d)
        """
        self.db_manager.run_cypher(query)