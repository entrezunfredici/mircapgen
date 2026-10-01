"""Adaptateur vers le SDK officiel `mcp` : seul module du framework qui l'importe.

Il construit un serveur MCP bas niveau dont la liste des tools et le traitement des
appels passent par le `Dispatcher` de Mircapgen (identification, visibilité, autorisation,
validation, audit). Le reste du framework ignore tout du protocole.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.lowlevel import Server
from mcp_types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from mircapgen.core.dispatcher import Dispatcher
from mircapgen.errors import MircapError
from mircapgen.rbac.models import Identity

IdentitySource = Callable[[Any], Awaitable[Identity | None]]
"""Renvoie l'identité de l'appelant pour la requête en cours, ou `None`."""

IDENTITY_CLAIM = "mircap_identity"


async def identity_from_access_token(_ctx: Any) -> Identity | None:
    """Lit l'identité posée par la vérification de l'identifiant d'accès (HTTP).

    Args:
        _ctx: Contexte de la requête MCP (non utilisé : l'identité vient du jeton).

    Returns:
        L'identité vérifiée, ou `None` si la requête n'est pas authentifiée.
    """
    token = get_access_token()
    if token is None or token.claims is None:
        return None
    identity = token.claims.get(IDENTITY_CLAIM)
    return identity if isinstance(identity, Identity) else None


def fixed_identity(identity: Identity | None) -> IdentitySource:
    """Source d'identité constante, utilisée par les tests en mémoire.

    Args:
        identity: Identité à renvoyer pour toute requête, ou `None` pour un appel anonyme.

    Returns:
        Une source d'identité.
    """

    async def source(_ctx: Any) -> Identity | None:
        return identity

    return source


def build_server(
    name: str,
    *,
    version: str,
    instructions: str | None,
    dispatcher: Dispatcher,
    identity_source: IdentitySource,
) -> Server[Any]:
    """Construit le serveur MCP d'une application.

    Args:
        name: Nom du service.
        version: Version du service.
        instructions: Texte d'accompagnement transmis à l'agent (Helper).
        dispatcher: Pipeline qui applique visibilité, autorisation et audit.
        identity_source: Fournit l'identité de l'appelant pour chaque requête.

    Returns:
        Un serveur MCP bas niveau, prêt à être servi en HTTP ou testé en mémoire.
    """

    async def on_list_tools(ctx: Any, _params: PaginatedRequestParams | None) -> ListToolsResult:
        identity = await identity_source(ctx)
        tools = [
            Tool(
                name=item.name,
                title=item.spec.label,
                description=item.description,
                input_schema=_input_schema(item.input_model),
            )
            for item in dispatcher.visible_features(identity)
        ]
        return ListToolsResult(tools=tools)

    async def on_call_tool(ctx: Any, params: CallToolRequestParams) -> CallToolResult:
        identity = await identity_source(ctx)
        try:
            result = await dispatcher.call(
                identity,
                params.name,
                params.arguments,
                request_id=str(ctx.request_id),
            )
        except MircapError as error:
            return CallToolResult(
                content=[TextContent(text=error.message)],
                is_error=True,
            )
        text = json.dumps(result, ensure_ascii=False)
        return CallToolResult(
            content=[TextContent(text=text)],
            structured_content=result if isinstance(result, dict) else None,
        )

    return Server(
        name,
        version=version,
        instructions=instructions,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


def _input_schema(model: Any) -> dict[str, Any]:
    schema: dict[str, Any] = model.model_json_schema()
    schema.pop("title", None)
    return schema
