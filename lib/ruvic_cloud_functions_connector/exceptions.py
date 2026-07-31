"""Jerarquía de excepciones del conector Google Cloud Functions."""

from __future__ import annotations


class CloudFunctionsConnectorError(Exception):
    """Error base del conector Google Cloud Functions."""


class CloudFunctionsAuthError(CloudFunctionsConnectorError):
    """Credenciales inválidas o cuenta de servicio sin permiso suficiente."""


class CloudFunctionsNetworkError(CloudFunctionsConnectorError):
    """Error de red o timeout al conectar con Google Cloud Functions."""


class CloudFunctionsDataError(CloudFunctionsConnectorError):
    """Función inexistente u otro error de datos."""
