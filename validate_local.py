"""Validación local del conector cloud_functions: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_CLOUD_FUNCTIONS_* exportadas en el entorno,
apuntando a una función de prueba desplegada con trigger HTTP.

ADVERTENCIA: este script INVOCA la función real configurada.
Ejecútalo solo contra una función de pruebas.
"""

from ruvic_cloud_functions_connector import CloudFunctionsClient, setup_logging

setup_logging("INFO")
client = CloudFunctionsClient()

print("== 1. Listar funciones de la región ==")
funciones = client.list_functions()
print(f"  {len(funciones)} función(es) encontrada(s)")

print("== 2. Consultar estado de la función configurada ==")
estado = client.get_status()
print(f"  {estado}")

print("== 3. Invocar la función configurada ==")
resultado = client.invoke({"origen": "validate_local.py"})
print(f"  status={resultado['status_code']}")

print("\nTodo OK: list_functions, get_status e invoke funcionan.")
