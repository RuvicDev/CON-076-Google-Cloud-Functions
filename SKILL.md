---
name: cloud-functions
description: Invocar una Google Cloud Function HTTP, listar funciones desplegadas y consultar su estado
---

# Google Cloud Functions

Conector de invocación y gestión de Google Cloud Functions (2nd gen).

## Credenciales

Usa una cuenta de servicio de Google Cloud (JSON completo). La
gestión (listar, consultar estado) usa
`google.cloud.functions_v2.FunctionServiceClient`; la invocación usa
un ID token firmado por la cuenta de servicio
(`google.oauth2.service_account.IDTokenCredentials`). Nunca
hardcodees ni loguees el contenido del JSON. La cuenta de servicio
debe tener asignados, limitados al proyecto o a la función:

- **"Cloud Functions Viewer"** — requerido para `list_functions` y
  `get_status`.
- **"Cloud Functions Invoker"** — requerido para `invoke`.

No uses el rol "Cloud Functions Admin".

## Capacidades

### `invoke(payload: dict | None = None) -> dict`

Invoca la función HTTP configurada con un payload JSON. Ejecuta
código real; no hay modo dry-run. Solo funciona con funciones que
tengan trigger HTTP.

```python
resultado = client.invoke({"nombre": "Ruvic"})
```

### `list_functions() -> list[dict]`

Lista las funciones desplegadas en la región configurada (name,
state, update_time). Solo lectura.

```python
funciones = client.list_functions()
```

### `get_status() -> dict`

Consulta el estado de despliegue de la función configurada. Solo
lectura.

```python
estado = client.get_status()
```

## Manejo de errores

Todas las excepciones heredan de `CloudFunctionsConnectorError`:

- `CloudFunctionsAuthError`: credenciales inválidas o rol IAM
  insuficiente.
- `CloudFunctionsNetworkError`: Cloud Functions inalcanzable o límite
  de cuota temporal.
- `CloudFunctionsDataError`: función inexistente, o función sin
  trigger HTTP al intentar `invoke`.

Nunca dejes propagar excepciones crudas de `google.api_core.exceptions.*`
ni de `requests` — siempre se traducen a estas.

## Buenas prácticas

- Tratá `invoke` como una operación que ejecuta código real con
  posibles efectos secundarios (la función puede escribir en otros
  sistemas); no la ejecutes contra una función de producción sin
  confirmar con el usuario.
- `list_functions` y `get_status` son seguras de ejecutar libremente
  (solo lectura).
- Si `invoke` falla con un error de datos indicando que la función no
  tiene URL invocable, es porque la función usa un trigger de eventos
  (Pub/Sub, Storage, etc.), no HTTP — explicaselo al usuario en vez
  de reintentar.
