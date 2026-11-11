"""Task-scoped Bilibili HTTPX transport (upstream 78d6dd6, MIT).

17.4.2's Api, buvid activation, ticket and WBI helpers resolve get_client
in network's globals. Do not select a process-wide client or patch Api.request:
the latter misses helper requests and would risk changing write retry behavior.
The inert dispatcher survives module reload; only the current task's binding
changes. It owns no sessions. BiliClient owns and closes its dedicated session.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from bilibili_api.clients.HTTPXClient import HTTPXClient
from bilibili_api.utils import network


_context = getattr(network.get_client, "_autopilot_context", None)
if _context is None:
    _context: ContextVar[Optional[HTTPXClient]] = ContextVar("bilibili_autopilot_httpx", default=None)

    def _get_client(original=network.get_client, context=_context):
        client = context.get()
        return client if client is not None else original()

    _get_client._autopilot_context = _context
    network.get_client = _get_client


@contextmanager
def api_transport(client: HTTPXClient) -> Iterator[None]:
    token = _context.set(client)
    try:
        yield
    finally:
        _context.reset(token)


def create_api_client() -> HTTPXClient:
    # Keep the library's configured proxy, environment policy and timeout.
    # Snapshot at plugin creation; no mutation of shared settings or pools.
    # TLS verification is always enabled, even if a global caller disabled it.
    settings = network.request_settings
    return HTTPXClient(proxy=settings.get_proxy(), timeout=settings.get_timeout(),
                       trust_env=settings.get_trust_env(), verify_ssl=True)
