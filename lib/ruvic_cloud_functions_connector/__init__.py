"""Conector Ruvic para Google Cloud Functions: invocación, listado y estado."""

from .client import CloudFunctionsClient
from .config import CloudFunctionsConfig, ENV_PREFIX
from .exceptions import (
    CloudFunctionsAuthError,
    CloudFunctionsConnectorError,
    CloudFunctionsDataError,
    CloudFunctionsNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "CloudFunctionsAuthError",
    "CloudFunctionsClient",
    "CloudFunctionsConfig",
    "CloudFunctionsConnectorError",
    "CloudFunctionsDataError",
    "CloudFunctionsNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
