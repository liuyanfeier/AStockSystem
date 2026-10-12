import os
from pathlib import Path
import subprocess
import sys

import pytest

from astock.research.core import ResearchError
from astock.research.publication import publish_bytes


def test_mid_write_then_recover(tmp_path, monkeypatch):
    target = tmp_path / 'object'
    original = Path.write_bytes
    def broken(self, body):
        original(self, body[:2])
        raise OSError('simulated disk failure')
    with monkeypatch.context() as m:
        m.setattr(Path, 'write_bytes', broken)
        with pytest.raises(OSError):
            publish_bytes(target, b'complete')
    assert not target.exists()
    assert not list(tmp_path.glob('.pending-*'))
    publish_bytes(target, b'complete')
    publish_bytes(target, b'complete')
    with pytest.raises(ResearchError):
        publish_bytes(target, b'different')
    assert target.read_bytes() == b'complete'


def test_process_interruption_keeps_final_absent(tmp_path):
    target = tmp_path / 'object'
    script = '''
import os, sys
from pathlib import Path
from astock.data.raw_writer import atomic_new_file
def interrupted(p):
    p.write_bytes(b'partial')
    os._exit(17)
atomic_new_file(Path(sys.argv[1]), interrupted)
'''
    result = subprocess.run([sys.executable, '-c', script, str(target)], check=False)
    assert result.returncode == 17 and not target.exists()
    # Stranded temporary bytes are never a final object or recovery prerequisite.
    assert list(tmp_path.glob('.pending-*'))
    publish_bytes(target, b'complete')
    assert target.read_bytes() == b'complete'


def test_report_pair_recovery(tmp_path, monkeypatch):
    from astock.reports import research
    snapshot = {'minimal': 'fixture'}
    monkeypatch.setattr(research, 'markdown', lambda s: 'rendered\n')
    original = research.publish_bytes
    def fail_second(path, body):
        if path.suffix == '.md':
            raise OSError('stop after snapshot')
        original(path, body)
    with monkeypatch.context() as m:
        m.setattr(research, 'publish_bytes', fail_second)
        with pytest.raises(OSError):
            research.publish(snapshot, tmp_path)
    run = research.publish(snapshot, tmp_path)
    assert (tmp_path / f'{run}.report.md').read_text() == 'rendered\n'
