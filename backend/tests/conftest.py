import shutil
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def isolate_lab_runtime_metadata_for_tests():
    """
    Keep API tests independent from file-backed lab runtime metadata.
    """
    from app.db import models  # noqa: F401 - register SQLAlchemy models
    from app.db.base import Base
    from app.db.session import engine
    from app.services.containerlab_adapter import GENERATED_DIR
    from app.services.session_service import _sessions

    Base.metadata.create_all(bind=engine)

    _sessions.clear()

    if GENERATED_DIR.exists():
        shutil.rmtree(GENERATED_DIR)

    yield

    _sessions.clear()

    if GENERATED_DIR.exists():
        shutil.rmtree(GENERATED_DIR)
