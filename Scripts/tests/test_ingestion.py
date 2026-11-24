"""Ingestion unit tests (Part A). Fake responses only: no internet, keys, or GCP needed."""

import pytest
import requests

from Scripts.ingestion import http_client, prices, registrations, stations
from Scripts.ingestion.storage import RawStore


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def no_sleep(_seconds):
    return None


def test_retry_then_success(monkeypatch):
    responses = iter([FakeResponse(503), FakeResponse(200, {"ok": True})])
    monkeypatch.setattr(requests, "get", lambda *a, **k: next(responses))
    assert http_client.get_with_retry("http://x", sleep=no_sleep).json() == {"ok": True}


def test_wrong_key_is_not_retried(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return FakeResponse(403)

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(requests.HTTPError):
        http_client.get_with_retry("http://x", sleep=no_sleep)
    assert len(calls) == 1


def test_missing_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("NREL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NREL_API_KEY"):
        http_client.require_env("NREL_API_KEY")


def test_phone_numbers_are_removed():
    rows = [{"id": 1, "station_phone": "555-0100", "city": "Chicago"}]
    assert stations.remove_pii(rows) == [{"id": 1, "city": "Chicago"}]


def test_eia_pagination_collects_every_page(monkeypatch):
    monkeypatch.setenv("EIA_API_KEY", "test")
    monkeypatch.setattr(prices.config, "EIA_PAGE_SIZE", 2)
    pages = iter(
        [
            {"response": {"total": "3", "data": [{"period": "2026-01"}, {"period": "2026-02"}]}},
            {"response": {"total": "3", "data": [{"period": "2026-03"}]}},
        ]
    )

    def getter(*args, **kwargs):
        return FakeResponse(200, next(pages))

    assert len(prices.fetch_all(getter=getter)) == 3


def test_registration_table_is_parsed():
    html = (
        "<table><tr><th>State</th><th>Electric (EV)</th></tr>"
        "<tr><td>Illinois</td><td>164,900</td></tr></table>"
    )
    df = registrations.parse_year(html, 2025)
    assert list(df.columns)[:2] == ["year", "State"]
    assert df.loc[0, "State"] == "Illinois"


def test_registration_layout_change_is_caught():
    with pytest.raises(ValueError):
        registrations.parse_year("<table><tr><th>Name</th></tr><tr><td>x</td></tr></table>", 2025)


def test_local_store_uses_date_then_source_layout(tmp_path):
    store = RawStore(bucket="", prefix="raw", local_dir=tmp_path)
    store.write_text(store.key("2026-11-20", "demo", "a.txt"), "hello")
    assert (tmp_path / "raw/2026-11-20/demo/a.txt").read_text() == "hello"
