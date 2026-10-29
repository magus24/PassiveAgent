import asyncio
import logging
import os
from pathlib import Path
import uvicorn
from api.main import app
from config.settings import settings
from collector.telegram_listener import collector
from storage.db import init_db
from graph.graph_builder import graph_builder

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def start_api():
    config = uvicorn.Config(app, host=settings.API_HOST, port=settings.API_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def start_collector():
    # Wait a bit for DB to initialize before starting collector
    await asyncio.sleep(2)
    await collector.start()

async def start_frontend():
    """Start the Vite frontend development server."""
    logger.info("Starting Frontend (Vite)...")
    # On Windows, npm is usually npm.cmd
    cmd = "npm.cmd run dev" if os.name == 'nt' else "npm run dev"
    env = os.environ.copy()
    env["VITE_API_URL"] = f"http://localhost:{settings.API_PORT}"
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(FRONTEND_DIR),
            env=env,
        )
        # Wait for the process to complete (it will run until interrupted)
        await process.wait()
    except Exception as e:
        logger.error(f"Failed to start frontend: {e}")

async def shutdown():
    """Graceful shutdown: close Neo4j driver and Telegram client."""
    logger.info("Running graceful shutdown...")
    try:
        await graph_builder.close()
        logger.info("Neo4j driver closed.")
    except Exception as e:
        logger.error(f"Error closing Neo4j driver: {e}")

    try:
        if collector.client and collector.client.is_connected():
            await collector.client.disconnect()
            logger.info("Telegram client disconnected.")
    except Exception as e:
        logger.error(f"Error disconnecting Telegram client: {e}")

async def main():
    logger.info("Initializing Database...")
    await init_db()
    
    logger.info("Starting PassiveAgent Components...")
    
    try:
        # Run the FastAPI server, Telegram Collector, and Frontend concurrently
        await asyncio.gather(
            start_api(),
            start_collector(),
            start_frontend()
        )
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down PassiveAgent...")
