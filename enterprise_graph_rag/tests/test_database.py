import pytest
from knowledge_engine.core.database import GraphDatabaseManager
from knowledge_engine.core.exceptions import DatabaseConnectionError

# Mocking would be used here in a real CI/CD pipeline.
# For this 'integration' test, we assume the DB is up.

def test_singleton_pattern():
    db1 = GraphDatabaseManager.get_instance()
    db2 = GraphDatabaseManager.get_instance()
    assert db1 is db2

def test_health_check():
    db = GraphDatabaseManager.get_instance()
    assert db.health_check() is True

def test_cypher_execution():
    db = GraphDatabaseManager.get_instance()
    # Simple calculation query that doesn't touch disk heavily
    result = db.run_cypher("RETURN 1+1 AS result")
    assert result[0]['result'] == 2