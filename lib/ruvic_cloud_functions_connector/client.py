"""Cliente de gestión e invocación de Google Cloud Functions.

Capacidades:
- invoke():         invoca la función configurada (HTTPS trigger) con un payload.
- list_functions(): lista las funciones desplegadas en la región configurada.
- get_status():     consulta el estado de despliegue de la función configurada.

Las credenciales SIEMPRE provienen de variables de entorno
RUVIC_CLOUD_FUNCTIONS_* (ver config.CloudFunctionsConfig.from_env).
Prohibido hardcodearlas.

El conector opera sobre una única función configurada para invoke()/
get_status() (principio de mínimo privilegio); list_functions() lista
todas las funciones de la región para fines de descubrimiento.
"""

from __future__ import annotations

from typing import Any

import google.auth.transport.requests
import requests
from google.api_core.exceptions import (
    Forbidden,
    GoogleAPICallError,
    NotFound,
    ServiceUnavailable,
    Unauthorized,
)
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.cloud import functions_v2
from google.oauth2 import service_account
from google.oauth2.service_account import IDTokenCredentials
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from .config import CloudFunctionsConfig
from .exceptions import (
    CloudFunctionsAuthError,
    CloudFunctionsConnectorError,
    CloudFunctionsDataError,
    CloudFunctionsNetworkError,
)
from .logging_utils import get_logger


def _wrap_error(exc: GoogleAPICallError, not_found_message: str) -> CloudFunctionsConnectorError:
    """Traduce un error de la API de Cloud Functions a una excepción propia,
    sin dejar escapar nunca el tipo crudo del SDK."""
    if isinstance(exc, (Forbidden, Unauthorized)):
        return CloudFunctionsAuthError(
            "Credenciales inválidas o sin permiso IAM suficiente sobre esta "
            "función. Revisa el rol asignado a la cuenta de servicio."
        )
    if isinstance(exc, NotFound):
        return CloudFunctionsDataError(not_found_message)
    if isinstance(exc, ServiceUnavailable):
        return CloudFunctionsNetworkError(
            "Google Cloud Functions no respondió correctamente. Puede ser un "
            "límite de cuota temporal; reintenta en unos segundos."
        )
    return CloudFunctionsDataError(f"Error de datos: {exc}")


class CloudFunctionsClient:
    """Cliente de Google Cloud Functions sobre la función configurada.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_CLOUD_FUNCTIONS_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = CloudFunctionsClient()  # lee RUVIC_CLOUD_FUNCTIONS_* del entorno
        >>> client.get_status()
    """

    def __init__(self, config: CloudFunctionsConfig | None = None) -> None:
        self.config = config or CloudFunctionsConfig.from_env()
        self._logger = get_logger()
        self._mgmt_client: functions_v2.FunctionServiceClient | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_credentials(self) -> service_account.Credentials:
        try:
            return service_account.Credentials.from_service_account_info(
                self.config.service_account_info
            )
        except (ValueError, KeyError) as exc:
            raise CloudFunctionsAuthError(
                f"El JSON de la cuenta de servicio es inválido o le faltan campos: {exc}"
            ) from exc

    def _get_mgmt_client(self) -> functions_v2.FunctionServiceClient:
        if self._mgmt_client is None:
            self._mgmt_client = functions_v2.FunctionServiceClient(
                credentials=self._get_credentials()
            )
        return self._mgmt_client

    def _project_id(self) -> str:
        return self.config.service_account_info["project_id"]

    def _function_path(self) -> str:
        return (
            f"projects/{self._project_id()}/locations/{self.config.region}"
            f"/functions/{self.config.function_name}"
        )

    def ping(self) -> bool:
        """Verifica la conexión consultando el estado de la función configurada.

        Returns:
            True si la conexión funciona.

        Raises:
            CloudFunctionsAuthError / CloudFunctionsNetworkError / CloudFunctionsDataError.
        """
        self.get_status()
        self._logger.info("Ping exitoso a la función %s", self.config.function_name)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: invocar la función
    # ------------------------------------------------------------------ #

    def invoke(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoca la función configurada (HTTPS trigger) con un payload JSON.

        Args:
            payload: cuerpo JSON a enviar en la invocación (opcional).

        Returns:
            Dict con: status_code, body (texto de la respuesta).

        Ejemplo:
            >>> client.invoke({"nombre": "Ruvic"})
            {'status_code': 200, 'body': '{"saludo": "Hola Ruvic"}'}
        """
        try:
            function = self._get_mgmt_client().get_function(
                request={"name": self._function_path()}
            )
        except (RefreshError, GoogleAuthError) as exc:
            raise CloudFunctionsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"La función {self.config.function_name!r} no existe."
            ) from exc

        url = function.service_config.uri
        if not url:
            raise CloudFunctionsDataError(
                f"La función {self.config.function_name!r} no tiene una URL HTTPS "
                "invocable (¿es una función con trigger de eventos, no HTTP?)."
            )

        try:
            id_token_credentials = IDTokenCredentials.from_service_account_info(
                self.config.service_account_info, target_audience=url
            )
            id_token_credentials.refresh(google.auth.transport.requests.Request())
        except (RefreshError, GoogleAuthError, ValueError, KeyError) as exc:
            raise CloudFunctionsAuthError(
                f"No se pudo obtener un ID token para invocar la función: {exc}"
            ) from exc

        try:
            response = requests.post(
                url,
                json=payload or {},
                headers={"Authorization": f"Bearer {id_token_credentials.token}"},
                timeout=self.config.connect_timeout,
            )
        except Timeout as exc:
            raise CloudFunctionsNetworkError(f"Timeout invocando la función: {exc}") from exc
        except RequestsConnectionError as exc:
            raise CloudFunctionsNetworkError(f"No se pudo conectar a la función: {exc}") from exc

        if response.status_code in (401, 403):
            raise CloudFunctionsAuthError(
                f"Sin permiso para invocar la función ({response.status_code})."
            )
        self._logger.info(
            "Función %s invocada (status %d)", self.config.function_name, response.status_code
        )
        return {"status_code": response.status_code, "body": response.text}

    # ------------------------------------------------------------------ #
    # Capacidad 2: listar funciones
    # ------------------------------------------------------------------ #

    def list_functions(self) -> list[dict[str, Any]]:
        """Lista las funciones desplegadas en la región configurada.

        Returns:
            Lista de dicts: {"name", "state", "update_time"}.

        Ejemplo:
            >>> client.list_functions()
            [{'name': 'mi-funcion', 'state': 'ACTIVE', ...}]
        """
        parent = f"projects/{self._project_id()}/locations/{self.config.region}"
        try:
            functions = self._get_mgmt_client().list_functions(request={"parent": parent})
            result = [
                {
                    "name": fn.name.split("/")[-1],
                    "state": functions_v2.Function.State(fn.state).name,
                    "update_time": fn.update_time.isoformat() if fn.update_time else None,
                }
                for fn in functions
            ]
        except (RefreshError, GoogleAuthError) as exc:
            raise CloudFunctionsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"La región {self.config.region!r} no existe o no es accesible."
            ) from exc
        self._logger.info("Listadas %d funciones en %s", len(result), self.config.region)
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 3: estado de despliegue
    # ------------------------------------------------------------------ #

    def get_status(self) -> dict[str, Any]:
        """Consulta el estado de despliegue de la función configurada.

        Returns:
            Dict con: name, state, update_time.

        Ejemplo:
            >>> client.get_status()
            {'name': 'mi-funcion', 'state': 'ACTIVE', 'update_time': '...'}
        """
        try:
            function = self._get_mgmt_client().get_function(
                request={"name": self._function_path()}
            )
        except (RefreshError, GoogleAuthError) as exc:
            raise CloudFunctionsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"La función {self.config.function_name!r} no existe."
            ) from exc

        result = {
            "name": self.config.function_name,
            "state": functions_v2.Function.State(function.state).name,
            "update_time": function.update_time.isoformat() if function.update_time else None,
        }
        self._logger.info("Estado de %s: %s", self.config.function_name, result["state"])
        return result
