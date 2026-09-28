"""
Unit tests for Runner BaseWorker and WorkerSignals.
"""

from unittest.mock import MagicMock
import pytest
from delphis.core.runner import BaseWorker, WorkerSignals

def test_base_worker_signals(qapp):
    worker = BaseWorker()
    assert isinstance(worker.signals, WorkerSignals)

    logs = []
    progress_updates = []
    cancelled = []

    worker.signals.output_line.connect(lambda msg, lvl: logs.append((msg, lvl)))
    worker.signals.progress.connect(lambda cur, tot: progress_updates.append((cur, tot)))
    worker.signals.cancelled.connect(lambda: cancelled.append(True))

    worker.log("Test log message", "info")
    assert len(logs) == 1
    assert logs[0] == ("Test log message", "info")

    worker.set_progress(5, 10)
    assert len(progress_updates) == 1
    assert progress_updates[0] == (5, 10)

    assert worker.is_cancelled is False
    worker.cancel()
    assert worker.is_cancelled is True
    assert len(cancelled) == 1
