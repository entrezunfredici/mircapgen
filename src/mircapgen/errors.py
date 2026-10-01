"""Hiérarchie d'erreurs standard du framework.

Une exception Python brute ne doit jamais atteindre un agent : tout ce qui sort du
framework passe par une sous-classe de `MircapError`, dont le message est sûr à
afficher (ni secret, ni détail interne).
"""

from __future__ import annotations


class MircapError(Exception):
    """Erreur de base de Mircapgen.

    Attributes:
        code: Identifiant stable de l'erreur, utilisable par un client.
        message: Message en français, sûr à transmettre à un agent.
    """

    code: str = "mircap_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthenticationError(MircapError):
    """Identifiant d'accès absent, invalide, expiré ou révoqué."""

    code = "authentication_error"


class AuthorizationError(MircapError):
    """L'utilisateur n'a pas le droit d'effectuer l'action demandée."""

    code = "authorization_error"


class ValidationError(MircapError):
    """Les paramètres reçus ne respectent pas le schéma de la Feature."""

    code = "validation_error"


class ConfigurationError(MircapError):
    """La configuration ou la déclaration d'une Feature est invalide."""

    code = "configuration_error"


class FeatureError(MircapError):
    """Erreur levée volontairement par une Feature, à destination de l'agent."""

    code = "feature_error"


class UnknownFeatureError(MircapError):
    """Feature inconnue **ou invisible** pour l'appelant.

    Une Feature à laquelle l'utilisateur n'a pas droit est volontairement signalée comme
    inconnue, pour ne pas révéler son existence (cahier des charges §9.1).
    """

    code = "unknown_feature"


class InternalError(MircapError):
    """Erreur interne inattendue. Les détails ne sont jamais transmis à l'agent."""

    code = "internal_error"
