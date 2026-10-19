"""Flywheel batch processing pipeline (SPEC 1.5.2)."""

import asyncio
import logging
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.core.flywheel import process_flywheel_batch
from app.core.llm import get_chat_model
from app.db.base import create_engine
from app.db.repositories.flywheel import FlywheelRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flywheel_pipeline")


async def run_flywheel(batch_size: int = 50) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repo = FlywheelRepository(factory)

    model = None
    try:
        model = get_chat_model(streaming=False)
    except Exception:
        logger.warning("No LLM configured, using rule-based flywheel normalization")

    logger.info("Starting flywheel batch processing...")
    result = await process_flywheel_batch(repo, model=model, batch_size=batch_size)
    logger.info(
        "Flywheel completed: processed=%d, merged=%d, new_items=%d",
        result["processed"],
        result["merged"],
        result["new_items"],
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_flywheel())
