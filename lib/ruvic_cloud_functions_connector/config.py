"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_CLOUD_FUNCTIONS_.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

ENV_PREFIX = "RUVIC_CLOUD_FUNCTIONS_"


@dataclass(frozen=True)
class CloudFunctionsConfig:
    """Parámetros de conexión a Google Cloud Functions."""

    service_account_info: dict[str, Any]
    region: str
    function_name: str
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "CloudFunctionsConfig":
        """Construye la configuración desde las variables RUVIC_CLOUD_FUNCTIONS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria o el JSON de
                la cuenta de servicio no es válido.

        Ejemplo:
            >>> config = CloudFunctionsConfig.from_env()
            >>> config.function_name
            'mi-funcion'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("SERVICE_ACCOUNT_JSON", "REGION", "FUNCTION_NAME")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector cloud_functions: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )

        raw_json = os.environ[f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON"]
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON no contiene un JSON válido: {exc}. "
                "Verifica que copiaste el archivo de credenciales completo, sin "
                "recortar ni modificar su contenido."
            ) from exc

        missing_keys = [k for k in ("client_email", "private_key", "project_id") if k not in info]
        if missing_keys:
            raise ValueError(
                "El JSON de la cuenta de servicio no tiene el formato esperado "
                f"(faltan campos: {', '.join(missing_keys)}). Descárgalo de nuevo "
                "desde Google Cloud Console → IAM y administración → Cuentas de servicio."
            )

        return cls(
            service_account_info=info,
            region=os.environ[f"{ENV_PREFIX}REGION"],
            function_name=os.environ[f"{ENV_PREFIX}FUNCTION_NAME"],
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "10")),
        )
