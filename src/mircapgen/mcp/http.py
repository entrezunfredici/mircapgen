"""Service HTTP du MCP : vérification des clés et réponses 401."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser, BearerAuthBackend
from mcp.server.auth.provider import AccessToken
from starlette.applications import Starlette
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from mircapgen.auth.keys import authenticate_key
from mircapgen.mcp.server import IDENTITY_CLAIM
from mircapgen.store.base import Store

if TYPE_CHECKING:
    from mircapgen.app import MircapApp


class KeyTokenVerifier:
    """Vérifie les clés personnelles présentées en `Authorization: Bearer`.

    Implémente le protocole `TokenVerifier` du SDK.

    Args:
        store: Persistance où chercher les clés et les utilisateurs.
    """

    def __init__(self, store: Store) -> None:
        self._store = store

    async def verify_token(self, token: str) -> AccessToken | None:
        """Vérifie une clé et renvoie l'accès qu'elle ouvre, ou `None` si elle est refusée."""
        identity = await authenticate_key(self._store, token)
        if identity is None:
            return None
        return AccessToken(
            # La clé n'est jamais conservée dans le jeton d'accès.
            token="[masqué]",
            client_id=identity.credential_id or "key",
            scopes=[],
            subject=identity.user.id,
            claims={IDENTITY_CLAIM: identity},
        )


class CredentialGateMiddleware:
    """Répond 401 quand un identifiant est présenté mais refusé, ou exigé mais absent.

    Un identifiant invalide ne doit pas être traité comme un appel anonyme : le client
    doit savoir que sa clé est refusée. Sans en-tête `Authorization`, l'appel reste
    anonyme (Features publiques uniquement) sauf si `require_credential` est activé.
    """

    def __init__(self, app: ASGIApp, *, require_credential: bool) -> None:
        self.app = app
        self.require_credential = require_credential

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authenticated = isinstance(scope.get("user"), AuthenticatedUser)
        presented = any(
            name.lower() == b"authorization" and value.lower().startswith(b"bearer ")
            for name, value in scope.get("headers", [])
        )
        if (presented or self.require_credential) and not authenticated:
            await _send_unauthorized(send, presented)
            return
        await self.app(scope, receive, send)


async def _send_unauthorized(send: Send, presented: bool) -> None:
    message = "Identifiant d'accès refusé." if presented else "Identifiant d'accès requis."
    body = json.dumps({"error": "invalid_token", "message": message}, ensure_ascii=False).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"www-authenticate", b'Bearer error="invalid_token"'),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def build_http_app(app: MircapApp, *, host: str) -> Starlette:
    """Construit l'application HTTP d'un service.

    Args:
        app: Application Mircapgen.
        host: Adresse d'écoute prévue.

    Returns:
        Une application Starlette qui sert le MCP sur `/mcp`.
    """
    server: Any = app.server()
    starlette_app: Starlette = server.streamable_http_app(host=host)
    # L'ordre compte : le dernier middleware ajouté est le plus extérieur.
    starlette_app.add_middleware(
        CredentialGateMiddleware, require_credential=app.require_credential
    )
    starlette_app.add_middleware(AuthContextMiddleware)
    starlette_app.add_middleware(
        AuthenticationMiddleware, backend=BearerAuthBackend(KeyTokenVerifier(app.store))
    )
    return starlette_app
