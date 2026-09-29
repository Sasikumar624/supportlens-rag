from collections.abc import Iterator
from pathlib import Path
import re
import shutil

import pytest


@pytest.fixture
def test_workspace(request: pytest.FixtureRequest) -> Iterator[Path]:
    workspace_root = Path(__file__).resolve().parent / ".tmp"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
    workspace = workspace_root / safe_name
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    try:
        yield workspace
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)
