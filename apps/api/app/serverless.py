"""ASGI plumbing for hosting the API behind a path prefix.

The web app calls the API through a ``/api`` prefix (``apps/web/src/api.ts``)
so a single origin serves both and no CORS is involved. In development the Vite
proxy strips that prefix; in the container image nginx does. On a serverless
host neither exists, so the prefix is stripped here instead.

This lives in the application package, not in the platform entrypoint, so the
behaviour is covered by the API test suite rather than only by a deployment.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]
ASGIApp = Callable[[dict, Receive, Send], Awaitable[None]]


def strip_path_prefix(path: str, prefix: str) -> str:
    """Map a public prefixed path onto the FastAPI route table.

    A path that does not carry the prefix is returned unchanged, so the caller
    is correct whether or not the platform already stripped it upstream.
    """
    if not prefix or prefix == "/":
        return path
    if path == prefix:
        return "/"
    if path.startswith(prefix + "/"):
        return path[len(prefix) :]
    return path


class PrefixStripMiddleware:
    """Strip ``prefix`` from the request path before the wrapped app routes it.

    Rewrites a copy of the scope; the caller's scope is left alone.
    """

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = prefix.rstrip("/")

    async def __call__(self, scope, receive, send):  # noqa: ANN001, ANN204
        if scope.get("type") in {"http", "websocket"}:
            scope = dict(scope)
            scope["path"] = strip_path_prefix(scope.get("path", "/"), self.prefix)
            raw_path = scope.get("raw_path")
            if raw_path is not None:
                # raw_path is undecoded bytes; latin-1 round-trips every byte.
                decoded = raw_path.decode("latin-1")
                scope["raw_path"] = strip_path_prefix(decoded, self.prefix).encode("latin-1")
        await self.app(scope, receive, send)
