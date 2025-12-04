import typer
import sys
import asyncio
from knowledge_engine.core.logging import configure_logging, logger
from knowledge_engine.core.database import GraphDatabaseManager
from knowledge_engine.ingestion.loader import IngestionPipeline
from knowledge_engine.ingestion.cleaner import GraphCleaner # New
from knowledge_engine.retrieval.verifier import GraphVerifier

app = typer.Typer(help="Enterprise GraphRAG Management CLI")

@app.callback()
def setup():
    """Initialize Logging and Config before commands run."""
    configure_logging()

@app.command()
def ingest(directory: str = "./data/raw"):
    """Run the ASYNC ingestion pipeline."""
    logger.info("cli_command_received", command="ingest", target=directory)
    
    async def _run():
        pipeline = IngestionPipeline()
        return await pipeline.process_directory_async(directory)

    try:
        result = asyncio.run(_run())
        typer.echo(f"✅ Ingestion Complete: {result}")
        
        # Optimization: Auto-run cleanup after ingestion
        cleaner = GraphCleaner()
        cleaner.run_all()
        typer.echo(f"✨ Graph Cleanup Complete")
        
    except Exception as e:
        logger.critical("ingestion_fatal_error", error=str(e))
        sys.exit(1)

@app.command()
def clean():
    """Manually run entity resolution and cleanup."""
    try:
        cleaner = GraphCleaner()
        cleaner.run_all()
        typer.echo("✅ Graph optimized.")
    except Exception as e:
        logger.error("cleanup_failed", error=str(e))

@app.command()
def verify(query: str):
    """Run a verification query."""
    logger.info("cli_command_received", command="verify", query=query)
    try:
        verifier = GraphVerifier()
        verifier.verify_retrieval(query)
    except Exception as e:
        logger.error("verification_error", error=str(e))

@app.command()
def reset_db(confirm: bool = False):
    """Wipe database."""
    if not confirm:
        typer.echo("❌ Pass --confirm to delete.")
        return
    db = GraphDatabaseManager.get_instance()
    db.run_cypher("MATCH (n) DETACH DELETE n")
    logger.warning("database_cleared")
    typer.echo("✅ Database wiped.")

if __name__ == "__main__":
    app()