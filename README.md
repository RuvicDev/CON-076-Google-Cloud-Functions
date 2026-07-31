# Conector Google Cloud Functions (CON-076)

Conector Ruvic de invocación y gestión de Google Cloud Functions.
Permite invocar la función HTTP configurada con un payload, listar las
funciones desplegadas en la región configurada, y consultar el estado
de despliegue de la función configurada.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Google-Cloud-Functions.git#subdirectory=lib
```

Python 3.10+. Dependencias: `google-cloud-functions`, `google-auth`, `requests`.

## Permisos requeridos en Google Cloud

Creá una **cuenta de servicio dedicada** y otorgale, limitado al
proyecto o, idealmente, a la función específica:

- **"Cloud Functions Viewer"**: necesario para `list_functions` y
  `get_status`.
- **"Cloud Functions Invoker"**: necesario para `invoke`.

No otorgues el rol **"Cloud Functions Admin"** (permitiría desplegar,
modificar o eliminar funciones).

## Variables de entorno (`RUVIC_CLOUD_FUNCTIONS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_CLOUD_FUNCTIONS_SERVICE_ACCOUNT_JSON` | Sí | Contenido completo del JSON de la cuenta de servicio |
| `RUVIC_CLOUD_FUNCTIONS_REGION` | Sí | Región de las funciones (ej. `us-central1`) |
| `RUVIC_CLOUD_FUNCTIONS_FUNCTION_NAME` | Sí | Nombre de la función objetivo (para `invoke` y `get_status`) |
| `RUVIC_CLOUD_FUNCTIONS_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_CLOUD_FUNCTIONS_SERVICE_ACCOUNT_JSON="$(cat service-account.json)"
export RUVIC_CLOUD_FUNCTIONS_REGION=us-central1
export RUVIC_CLOUD_FUNCTIONS_FUNCTION_NAME=tu-funcion-de-prueba

python test_connection.py
python validate_local.py
```

## Notas de integración

- `list_functions` y `get_status` son de **solo lectura** (metadatos
  de despliegue). `invoke` **SÍ ejecuta código real** de la función
  — no hay modo dry-run.
- `invoke` solo funciona con funciones que tengan un **trigger HTTP**
  (2nd gen); las funciones con trigger de eventos (Pub/Sub, Storage,
  etc.) no exponen una URL invocable y `invoke` fallará con un error
  de datos.
- La autenticación para `invoke` usa un **ID token** firmado por la
  cuenta de servicio con audiencia igual a la URL de la función
  (`google.oauth2.service_account.IDTokenCredentials`), el mecanismo
  estándar para invocar Cloud Functions/Cloud Run autenticadas.
- La gestión (`list_functions`, `get_status`) usa el cliente oficial
  `google.cloud.functions_v2.FunctionServiceClient`.
