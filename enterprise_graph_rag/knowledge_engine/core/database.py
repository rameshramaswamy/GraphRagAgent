import logging
from typing import Any, List, Dict
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError
from tenacity import retry, stop_after_attempt, wait_fixed
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from knowledge_engine.core.config import settings
from knowledge_engine.core.exceptions import DatabaseConnectionError
from knowledge_engine.core.logging import logger

class GraphDatabaseManager:
    _instance = None
    
    def __init__(self):
        if GraphDatabaseManager._instance is not None:
            raise RuntimeError("Use get_instance()")
        
        self._driver: Driver = None
        self._store: Neo4jPropertyGraphStore = None
        self._connect()
        GraphDatabaseManager._instance = self

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _connect(self):
        try:
            logger.info("connecting_to_neo4j", uri=settings.NEO4J_URI)
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_lifetime=200
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            
            # Initialize LlamaIndex Store
            self._store = Neo4jPropertyGraphStore(
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD,
                url=settings.NEO4J_URI,
            )
            logger.info("neo4j_connected_successfully")
        except (ServiceUnavailable, AuthError) as e:
            logger.error("neo4j_connection_failed", error=str(e))
            raise DatabaseConnectionError(f"Failed to connect to Neo4j: {str(e)}")

    def get_store(self) -> Neo4jPropertyGraphStore:
        return self._store

    def health_check(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def run_cypher(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Safe execution of Cypher queries."""
        if not self._driver:
            raise DatabaseConnectionError("Driver not initialized")
        
        with self._driver.session() as session:
            try:
                result = session.run(query, params or {})
                return [record.data() for record in result]
            except Exception as e:
                logger.error("cypher_execution_failed", query=query, error=str(e))
                raise e

    def close(self):
        if self._driver:
            self._driver.close()
            logger.info("neo4j_driver_closed")