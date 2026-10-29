import asyncio
import logging
from config.settings import settings
import os

logger = logging.getLogger(__name__)

class SpiderfootRunner:
    def __init__(self):
        self.sf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spiderfoot", "sf.py")
        
    async def trigger_scan(self, target: str):
        """Trigger a SpiderFoot scan as an async subprocess.

        Uses asyncio.create_subprocess_exec instead of subprocess.Popen
        to avoid blocking the event loop.
        """
        logger.info(f"Triggering SpiderFoot scan for target: {target}")
        try:
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            python_candidates = [
                os.path.join(backend_dir, ".venv", "Scripts", "python.exe"),
                os.path.join(backend_dir, "venv", "Scripts", "python.exe"),
                "python",
            ]
            python_executable = next(
                (candidate for candidate in python_candidates if candidate == "python" or os.path.exists(candidate)),
                "python",
            )

            process = await asyncio.create_subprocess_exec(
                python_executable,
                self.sf_path,
                "-s", target,
                "-q",  # quiet mode
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            logger.info(f"SpiderFoot scan started for {target} (PID: {process.pid})")
        except Exception as e:
            logger.error(f"Failed to start SpiderFoot scan: {e}")

spiderfoot_runner = SpiderfootRunner()
