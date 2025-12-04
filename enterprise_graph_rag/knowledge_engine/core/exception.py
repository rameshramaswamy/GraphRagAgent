class GraphPlatformError(Exception):
    """Base exception for the platform."""
    pass

class DatabaseConnectionError(GraphPlatformError):
    """Raised when Neo4j is unreachable."""
    pass

class IngestionError(GraphPlatformError):
    """Raised when document parsing or indexing fails."""
    pass