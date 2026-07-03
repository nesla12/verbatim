"""Configurazione pytest: rende importabile il pacchetto e genera le fixture audio."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def fixtures():
    from tests.make_fixture import ensure_fixtures

    return ensure_fixtures()


@pytest.fixture(scope="session")
def load_wav():
    from app.pipeline.audio import load_wav as _lw

    return _lw
