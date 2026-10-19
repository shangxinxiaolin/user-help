"""Conversation QA knowledge mining pipeline (SPEC 1.5.3)."""

import asyncio
import logging
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.core.llm import get_chat_model
from app.db.base import create_engine
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.kb import KnowledgeRepository
from app.kb.mining import compute_qa_fingerprint, mine_qa_from_messages
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mine_knowledge")


async def run_mining() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    conv_repo = ConversationRepository(factory)
    kb_repo = KnowledgeRepository(factory)

    model = None
    try:
        model = get_chat_model(streaming=False)
    except Exception:
        logger.warning("No LLM configured, using heuristic QA mining")

    logger.info("Scanning conversations for QA mining...")
    # List staging fingerprints to deduplicate
    existing = await kb_repo.list_qa_staging(limit=500)
    seen = {e.fingerprint for e in existing}

    total_extracted = 0
    # Process sample conversation IDs
    for conv_id in range(1, 100):
        conv = await conv_repo.get_conversation(conv_id)
        if conv is None:
            continue
        msgs = await conv_repo.list_messages(conv_id)
        qa_pairs = await mine_qa_from_messages(msgs, model=model)
        for qa in qa_pairs:
            fp = compute_qa_fingerprint(qa["question"], qa["answer"])
            if fp not in seen:
                await kb_repo.add_qa_extraction(
                    question=qa["question"],
                    answer=qa["answer"],
                    fingerprint=fp,
                    conversation_id=conv_id,
                )
                seen.add(fp)
                total_extracted += 1

    logger.info("Conversation mining finished: %d new QA pairs extracted", total_extracted)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_mining())
