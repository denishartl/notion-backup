# ABOUTME: Tests for the transient-error retry decorator on the Notion client.
# ABOUTME: Verifies retries on timeouts/5xx/429 and immediate failure on permanent errors.

import httpx
import pytest

from notion_client.errors import (
    APIErrorCode,
    APIResponseError,
    RequestTimeoutError,
)

from notion_backup.notion import client as client_module
from notion_backup.notion.client import retry_on_transient_error


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Record sleeps without actually waiting."""
    sleeps = []
    monkeypatch.setattr(client_module.time, "sleep", lambda s: sleeps.append(s))
    return sleeps


def _api_error(status: int, code: APIErrorCode, headers: dict | None = None) -> APIResponseError:
    response = httpx.Response(status_code=status, headers=headers or {})
    return APIResponseError(response=response, message="boom", code=code)


def _flaky(sequence):
    """Build a decorated function that yields each item in sequence per call.

    Items that are Exceptions are raised; other items are returned.
    """
    state = {"n": 0}

    @retry_on_transient_error(max_retries=3)
    def fn():
        i = state["n"]
        state["n"] += 1
        item = sequence[i]
        if isinstance(item, Exception):
            raise item
        return item

    return fn, state


def test_retries_on_timeout_then_succeeds():
    fn, state = _flaky([RequestTimeoutError(), RequestTimeoutError(), "ok"])
    assert fn() == "ok"
    assert state["n"] == 3


def test_retries_on_server_error_then_succeeds():
    err = _api_error(503, APIErrorCode.ServiceUnavailable)
    fn, state = _flaky([err, "ok"])
    assert fn() == "ok"
    assert state["n"] == 2


def test_gives_up_after_max_retries_and_reraises():
    fn, state = _flaky([RequestTimeoutError(), RequestTimeoutError(), RequestTimeoutError()])
    with pytest.raises(RequestTimeoutError):
        fn()
    assert state["n"] == 3


def test_does_not_retry_on_object_not_found():
    err = _api_error(404, APIErrorCode.ObjectNotFound)
    fn, state = _flaky([err, "ok"])
    with pytest.raises(APIResponseError):
        fn()
    assert state["n"] == 1


def test_honors_retry_after_header_on_429(no_sleep):
    err = _api_error(429, APIErrorCode.RateLimited, headers={"Retry-After": "2"})
    fn, state = _flaky([err, "ok"])
    assert fn() == "ok"
    assert state["n"] == 2
    assert no_sleep == [2]
