from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import httpx
import pytest

import app.geocoding.providers as provider_module
from app.geocoding.models import GeocodingSearchRequest
from app.geocoding.providers import NominatimProvider
from app.geocoding.rate_limit import ApplicationRateLimiter


class ControlledClock:
    def __init__(self) -> None:
        self.current = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.current

    def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.current += delay


def test_first_request_can_proceed_without_waiting() -> None:
    clock = ControlledClock()
    limiter = ApplicationRateLimiter(clock=clock.now, sleep=clock.sleep)

    with limiter.slot():
        dispatch_time = clock.now()

    assert dispatch_time == 0.0
    assert clock.sleeps == []


def test_sequential_slots_are_at_least_one_second_apart() -> None:
    clock = ControlledClock()
    limiter = ApplicationRateLimiter(clock=clock.now, sleep=clock.sleep)
    dispatch_times: list[float] = []

    for _ in range(2):
        with limiter.slot():
            dispatch_times.append(clock.now())

    assert dispatch_times == [0.0, 1.0]
    assert dispatch_times[1] - dispatch_times[0] >= 1.0


def test_concurrent_slots_are_serialized_without_duplicate_slots() -> None:
    clock = ControlledClock()
    limiter = ApplicationRateLimiter(clock=clock.now, sleep=clock.sleep)
    dispatch_times: list[float] = []
    dispatch_lock = Lock()

    def dispatch() -> None:
        with limiter.slot():
            with dispatch_lock:
                dispatch_times.append(clock.now())

    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(lambda _: dispatch(), range(3)))

    assert sorted(dispatch_times) == [0.0, 1.0, 2.0]
    assert len(set(dispatch_times)) == 3


def test_default_limiter_is_shared_by_provider_instances_without_real_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = ControlledClock()
    shared_limiter = ApplicationRateLimiter(clock=clock.now, sleep=clock.sleep)
    monkeypatch.setattr(provider_module, "_SHARED_NOMINATIM_RATE_LIMITER", shared_limiter)
    dispatch_times: list[float] = []
    dispatch_lock = Lock()

    def handler(request: httpx.Request) -> httpx.Response:
        with dispatch_lock:
            dispatch_times.append(clock.now())
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "28.5457",
                    "lon": "77.1928",
                    "display_name": "IIT Delhi",
                    "licence": "Data © OpenStreetMap contributors, ODbL 1.0.",
                }
            ],
            request=request,
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as first_client,
        httpx.Client(transport=httpx.MockTransport(handler)) as second_client,
    ):
        first_provider = NominatimProvider(client=first_client)
        second_provider = NominatimProvider(client=second_client)

        def search(provider: NominatimProvider) -> None:
            provider.search(GeocodingSearchRequest(query="IIT Delhi"))

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(search, [first_provider, second_provider]))

    assert sorted(dispatch_times) == [0.0, 1.0]
    assert len(set(dispatch_times)) == 2
