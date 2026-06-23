import pytest

from backend.core.resolver_cache import cache


@pytest.fixture(autouse=True)
def _no_resolver_cache():
    """Disable the persistent URI cache during tests so each test sees real
    (mocked) Spotify search behavior and assertions on call counts hold."""
    cache.enabled = False
    cache.clear()
    yield
    cache.enabled = True
