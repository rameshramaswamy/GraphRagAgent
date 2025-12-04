import logging
from knowledge_engine.core.database import GraphDatabaseManager
from knowledge_engine.core.logging import logger
from knowledge_engine.core.config import settings

class GraphCleaner:
    def __init__(self):
        self.db = GraphDatabaseManager.get_instance()

    def deduplicate_entities(self):
        """
        Runs Cypher queries to merge duplicate entities based on name similarity.
        """
        logger.info("starting_graph_cleanup")
        
        # 1. Merge Case-Insensitive Duplicates
        # Example: 'alice' and 'Alice' -> Merged to 'Alice'
        query_case_merge = """
        MATCH (n:Entity)
        WITH toLower(n.name) as name_lower, collect(n) as nodes
        WHERE size(nodes) > 1
        CALL apoc.refactor.mergeNodes(nodes, {properties:"combine", mergeRels:true})
        YIELD node
        RETURN count(node) as merged_count
        """
        
        # Note: APOC is standard in Neo4j Enterprise/Aura. 
        # If APOC is missing, we would need a more complex Python-side logic.
        try:
            # We wrap this in try/catch in case APOC isn't installed
            results = self.db.run_cypher(query_case_merge)
            merged = results[0].get('merged_count', 0) if results else 0
            logger.info("deduplication_complete", merged_nodes=merged)
        except Exception as e:
            logger.warning("apoc_merge_failed", reason="Ensure APOC plugin is enabled in Neo4j", error=str(e))

    def remove_orphans(self):
        """Remove entities that have no connections (hallucinations)."""
        query = """
        MATCH (n:Entity)
        WHERE NOT (n)--()
        DELETE n
        RETURN count(n) as deleted_count
        """
        results = self.db.run_cypher(query)
        count = results[0]['deleted_count'] if results else 0
        logger.info("orphans_removed", count=count)

    def remove_noise_nodes(self):
        """
        Optimization: Remove nodes that do not strictly adhere to the Allowed Schema.
        This cleans up 'hallucinated' labels.
        """
        allowed = settings.ALLOWED_ENTITY_TYPES + ["Chunk"] # Always keep Chunks
        
        # Neo4j Cypher to find nodes that have labels NOT in our allow list
        # Note: Cypher labels are dynamic, so we check intersection.
        # This is a bit complex in Cypher, so a simpler approach is:
        # Match nodes that have NO allowed labels.
        
        labels_str = ":".join(allowed) # e.g. :Person:Organization:Project
        
        # Heuristic: If a node does NOT have any of the allowed labels, detach delete.
        # Constructing dynamic query:
        
        where_clause = " AND ".join([f"NOT n:{label}" for label in allowed])
        
        query = f"""
        MATCH (n)
        WHERE {where_clause}
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """
        
        try:
            results = self.db.run_cypher(query)
            count = results[0]['deleted_count'] if results else 0
            if count > 0:
                logger.info("noise_nodes_removed", count=count)
        except Exception as e:
            logger.warning("noise_cleanup_failed", error=str(e))

    def run_all(self):
        self.deduplicate_entities()
        self.remove_orphans()
        self.remove_noise_nodes()