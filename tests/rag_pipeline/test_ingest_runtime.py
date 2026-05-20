"""Tests voor institutionele ingest-runtime (timeouts)."""

from __future__ import annotations

import time

import pytest

from ingest_runtime import FileJobTimeout, run_file_job


def test_run_file_job_completes_within_timeout():
    assert run_file_job(lambda: 42, timeout_sec=5.0) == 42


def test_run_file_job_raises_on_timeout():
    def slow() -> None:
        time.sleep(2.0)

    with pytest.raises(FileJobTimeout):
        run_file_job(slow, timeout_sec=0.2)
