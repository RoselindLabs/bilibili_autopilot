"""Copy a pristine on-disk schema for business tests; never patch production IO.

Store/migration tests still construct StateStore directly. Each business test owns
its copied file; ordinary initialize/restart calls and all transactions run normally.
"""
import atexit
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from local_bilibili_autopilot.state import StateStore

_template = None


def fresh_store(path):
    global _template
    if _template is None:
        directory = TemporaryDirectory(prefix='bili-pristine-schema-')
        atexit.register(directory.cleanup)
        source = Path(directory.name) / 'empty.sqlite3'
        StateStore(source).initialize(now=0)
        _template = directory, source
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError('Fixture destination must be new')
    shutil.copyfile(_template[1], path)
    return StateStore(path)
