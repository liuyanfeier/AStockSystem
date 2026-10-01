"""Tests use synthetic inputs only and reject Python network access."""

import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in ("TUSHARE_TOKEN", "ASTOCK_DATA_DIR", "ASTOCK_DB_PATH"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("Network access is forbidden in Phase 0 tests.")

    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
