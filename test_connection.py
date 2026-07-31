"""Prueba de conexión estándar del conector cloud_functions.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_CLOUD_FUNCTIONS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a Google Cloud Functions y consulta el estado de la función
    configurada usando las env vars RUVIC_CLOUD_FUNCTIONS_*."""
    try:
        from ruvic_cloud_functions_connector import (
            CloudFunctionsAuthError,
            CloudFunctionsClient,
            CloudFunctionsDataError,
            CloudFunctionsNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-cloud-functions-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Google-Cloud-Functions.git#subdirectory=lib",
        )

    try:
        client = CloudFunctionsClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except CloudFunctionsAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except CloudFunctionsNetworkError as exc:
        return False, f"Error de red: {exc}"
    except CloudFunctionsDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a Google Cloud Functions (función={client.config.function_name!r})",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
