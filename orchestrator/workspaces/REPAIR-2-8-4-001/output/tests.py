# // Chg_TESTS_2609: Requirement 2.8.4 auth rotation & UA fallback coverage

import json
import sys
from pathlib import Path

import pytest
import requests

# // Chg_TESTS_PATH_2609: ensure project root is importable when running standalone
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.fetcher_v4 import VacancyFetcher, ExponentialBackoff
from core import auth


class _DummyDB:
    def save_vacancy(self, *_args, **_kwargs):
        return False

    def update_task_progress(self, *_args, **_kwargs):
        return None


class DummyResponse:
    def __init__(self, status_code, data=None, url="https://api.hh.ru/vacancies"):
        self.status_code = status_code
        self._data = data or {"items": [], "found": 0, "pages": 0}
        self.url = url
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._data

    @property
    def text(self):
        return json.dumps(self._data)


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset auth rotation state before each test to avoid cross-test bleed."""
    auth.reset_auth_state()
    yield
    auth.reset_auth_state()


def test_exponential_backoff_delays_and_limits(monkeypatch):
    backoff = ExponentialBackoff(base_delay=1.0, max_retries=4, jitter=False)
    captured_delays = []

    monkeypatch.setattr("plugins.fetcher_v4.time.sleep", lambda _value: None)

    for _ in range(4):
        captured_delays.append(backoff.wait_and_increment())

    # After max retries the delay should drop to 0 (no more retries)
    captured_delays.append(backoff.wait_and_increment())

    assert captured_delays[:4] == [1.0, 4.0, 16.0, 64.0]
    assert captured_delays[-1] == 0

    backoff.reset()
    assert backoff.should_retry(status_code=429)
    assert not backoff.should_retry(status_code=400)


def test_fetcher_user_agent_fallback_on_400(monkeypatch):
    fetcher = VacancyFetcher(config={"base_url": "https://api.hh.ru"}, database=_DummyDB())
    fetcher.ua_fallback_used = False
    initial_user_agent = fetcher.session.headers.get("User-Agent")

    responses = [
        DummyResponse(400),
        DummyResponse(200, {"items": [{"id": "123"}], "found": 1, "pages": 1})
    ]
    call_user_agents = []

    def fake_get(url, params=None, timeout=None):
        call_user_agents.append(fetcher.session.headers.get("User-Agent"))
        response = responses.pop(0)
        response.url = url
        return response

    monkeypatch.setattr(fetcher.session, "get", fake_get)

    items = fetcher._fetch_page({"params": {}}, page=0)

    assert fetcher.ua_fallback_used is True
    assert call_user_agents[0] == initial_user_agent
    assert call_user_agents[1] == fetcher.safe_browser_ua
    assert items == [{"id": "123"}]


def test_fetcher_drops_authorization_on_403(monkeypatch):
    fetcher = VacancyFetcher(config={"base_url": "https://api.hh.ru"}, database=_DummyDB())
    fetcher.ua_fallback_used = False
    fetcher.auth_disabled_fallback_used = False
    fetcher.session.headers["Authorization"] = "Bearer test-token"

    responses = [
        DummyResponse(403),
        DummyResponse(200, {"items": [{"id": "321"}], "found": 1, "pages": 1})
    ]

    def fake_get(url, params=None, timeout=None):
        response = responses.pop(0)
        response.url = url
        return response

    monkeypatch.setattr(fetcher.session, "get", fake_get)

    items = fetcher._fetch_page({"params": {}}, page=0)

    assert "Authorization" not in fetcher.session.headers
    assert fetcher.auth_disabled_fallback_used is True
    assert items == [{"id": "321"}]


def test_auth_provider_rotation_after_failure(monkeypatch):
    providers = auth.get_all_providers("download")
    if not providers:
        pytest.skip("No auth providers configured for download purpose")

    current = auth.choose_provider("download")
    current_name = current["name"]

    # Ensure there is at least one alternative provider available
    alternative_exists = any(candidate["name"] != current_name for candidate in providers)
    if not alternative_exists:
        pytest.skip("Only one provider configured; rotation is not applicable")

    auth.mark_provider_failed(current_name)
    rotated = auth.choose_provider("download")

    assert rotated["name"] != current_name
