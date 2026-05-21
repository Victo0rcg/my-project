"""
main.py — Coordinador principal del sistema de transacciones bancarias.

Este módulo integra los componentes funcionales del proyecto:
  - core/           : Motor de cuentas y transacciones (Módulo 1)
  - scheduling/     : Planificador SCAN de logs       (Módulo 2)
  - security/       : Control de acceso RBAC          (Módulo 3)
  - concurrency/    : Algoritmo del Banquero          (Módulo 4)

Su responsabilidad principal es inicializar los servicios, orquestar el
procesamiento de transacciones y registrar los resultados con la política
de planificación definida.
"""

import logging
import threading
import random
import os

from core.account import Account
from core.transaction import Transaction, TransactionType, TransactionBuilder
from core.transaction_engine import TransactionEngine
from scheduling.scan_scheduler import scan_scheduling
from security.roles import Rol, Operacion
from security.rbac_policy import PoliticaRBAC
from concurrency.bankers_guard import GuardiaBanquero


# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

_LOG_SYSTEM = "banco-transacciones-so/logs/system.log"
os.makedirs(os.path.dirname(_LOG_SYSTEM), exist_ok=True)

logging.basicConfig(
    filename=_LOG_SYSTEM,
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Sección 1: Integración RBAC con el motor de transacciones
#
# El motor de transacciones invoca el hook con una instancia Transaction cuyo
# atributo user_role es una cadena de texto. PoliticaRBAC opera con los enums
# Rol y Operacion, por lo que este componente traduce la solicitud y delega
# la decisión de autorización en la política establecida.
# ---------------------------------------------------------------------------

# Mapa de TransactionType → Operacion RBAC
_TIPO_A_OPERACION = {
    TransactionType.DEPOSIT:    Operacion.DEPOSITO,
    TransactionType.WITHDRAWAL: Operacion.RETIRO,
    TransactionType.TRANSFER:   Operacion.TRANSFERENCIA,
    TransactionType.QUERY:      Operacion.CONSULTA,
}

def construir_hook_rbac(politica: PoliticaRBAC):
    """
    Construye un hook de autorización para el motor de transacciones.

    El hook convierte el atributo user_role de la transacción al enum Rol,
    y el tipo de transacción al enum Operacion antes de consultar la política
    RBAC. Si el rol o la operación no son reconocidos, la transacción se
    considera no autorizada.

    Parámetros
    ----------
    politica : PoliticaRBAC
        Instancia de la política de control de acceso que será utilizada.

    Retorna
    -------
    Callable[[Transaction], bool]
        Función de autorización usada por el motor de transacciones.
    """
    def hook(transaction: Transaction) -> bool:
        try:
            rol = Rol(transaction.user_role)           # string → enum
        except ValueError:
            logging.error(f"[RBAC] Rol desconocido: '{transaction.user_role}'")
            return False

        operacion = _TIPO_A_OPERACION.get(transaction.transaction_type)
        if operacion is None:
            logging.error(f"[RBAC] Tipo de transacción sin mapeo RBAC: {transaction.transaction_type}")
            return False

        try:
            return politica.verificar_permiso(rol, operacion)
        except PermissionError:
            return False   # PoliticaRBAC lanza PermissionError cuando deniega

    return hook


# ---------------------------------------------------------------------------
# Sección 2: Integración del Algoritmo del Banquero con el motor
#
# GuardiaBanquero modela los recursos mediante matrices de procesos por
# tipos de recurso. En esta adaptación, el único recurso disputado en una
# transferencia es el lock de la cuenta origen.
#
# Adaptación al modelo de cuentas:
#   - Cada cuenta activa se considera como un proceso en el algoritmo.
#   - El único recurso es el lock de cuenta, representado como un vector.
#   - recursos_disponibles = [num_cuentas] (todos los locks libres al inicio)
#   - necesidad_maxima[i]  = [1]          (cada cuenta puede requerir 1 lock)
#   - recursos_asignados   = [[0], [0], ...] (ninguno asignado al inicio)
#
# Antes de procesar una transferencia se solicita un recurso adicional para la
# cuenta fuente. Si el Algoritmo del Banquero determina que el estado es
# seguro, la operación puede continuar; en caso contrario, se deniega.
# ---------------------------------------------------------------------------

def construir_guard_banquero(cuentas: dict):
    """
    Construye un guard para el Algoritmo del Banquero en el contexto bancario.

    Esta función adapta las solicitudes de transferencia del motor a una
    evaluación de seguridad de recursos en el Algoritmo del Banquero. Sólo
    las transacciones de tipo TRANSFER se someten a esta verificación.

    Parámetros
    ----------
    cuentas : dict
        Diccionario de cuentas bancarias presentes en el sistema.

    Retorna
    -------
    Callable[[Transaction], bool]
        Función que evalúa si una transferencia puede ejecutarse sin riesgo
        de bloquear el sistema.
    """
    n = len(cuentas)
    cuenta_ids = list(cuentas.keys())
    indice_cuenta = {cid: i for i, cid in enumerate(cuenta_ids)}

    # Estado inicial: todos los locks disponibles, nadie tiene nada asignado
    recursos_disponibles  = [n]          # 1 tipo de recurso: locks de cuenta
    necesidad_maxima      = [[1]] * n    # cada cuenta puede necesitar 1 lock
    recursos_asignados    = [[0]] * n    # ninguna cuenta tiene locks asignados

    guard = GuardiaBanquero(
        recursos_disponibles,
        necesidad_maxima,
        recursos_asignados,
    )

    lock_guard = threading.Lock()   # proteger el estado interno del banquero

    def bankers_hook(transaction: Transaction) -> bool:
        if transaction.transaction_type != TransactionType.TRANSFER:
            return True  # sólo aplica a transferencias

        idx = indice_cuenta.get(transaction.source_account_id)
        if idx is None:
            return True  # cuenta desconocida: deja que el motor la rechace

        with lock_guard:
            try:
                resultado = guard.solicitar_recursos(idx, [1])
                if resultado:
                    # Liberar el recurso simulado una vez aprobada la solicitud.
                    # La sincronización final de la transferencia se gestiona en
                    # la ejecución real del motor.
                    guard.recursos_disponibles[0] += 1
                    guard.recursos_asignados[idx][0] -= 1
                    guard.matriz_necesidad[idx][0]  += 1
                return resultado
            except ValueError as e:
                logging.warning(f"[BANQUERO] Error al evaluar solicitud: {e}")
                return False

    return bankers_hook


# ---------------------------------------------------------------------------
# Sección 3: Planificador SCAN aplicado a los logs de transacciones
#
# Después de que el motor termina de procesar las transacciones, se recuperan
# los resultados y se ordenan con SCAN antes de escribirlos en el log.
# Esto simula el subsistema de escritura en disco con planificación SCAN.
# ---------------------------------------------------------------------------

def registrar_resultados_con_scan(resultados: list, archivo_log: str = "banco-transacciones-so/logs/transactions.log"):
    """
    Ordena y registra los resultados de las transacciones usando planificación SCAN.

    El método aplica el algoritmo SCAN a los números de bloque asignados por el
    motor para simular la planificación de E/S de disco. Los resultados se
    escriben en el archivo de log especificado.

    Parámetros
    ----------
    resultados : list
        Lista de transacciones procesadas con su estado final.
    archivo_log : str, opcional
        Ruta del archivo de log en el que se almacenan los resultados.
    """
    os.makedirs(os.path.dirname(archivo_log), exist_ok=True)

    if not resultados:
        logging.info("[SCAN] No hay resultados que registrar.")
        return

    solicitudes  = [r.block_number for r in resultados]
    bloque_map   = {r.block_number: r for r in resultados}   # block → transacción
    # Si hay bloques repetidos, guardar lista
    bloque_lista: dict[int, list] = {}
    for r in resultados:
        bloque_lista.setdefault(r.block_number, []).append(r)

    cabezal_inicial = 0
    orden_scan = scan_scheduling(solicitudes, cabezal_inicial, direction='up')

    logging.info(f"[SCAN] Orden de escritura de bloques: {orden_scan}")

    with open(archivo_log, "a", encoding="utf-8") as f:
        for bloque in orden_scan:
            for txn in bloque_lista.get(bloque, []):
                linea = (
                    f"[{txn.transaction_id}] "
                    f"bloque={txn.block_number:03d} | "
                    f"{txn.transaction_type.value:<12} | "
                    f"cuenta={txn.source_account_id} | "
                    f"monto=${txn.amount:>10.2f} | "
                    f"rol={txn.user_role:<15} | "
                    f"estado={txn.status.value}\n"
                )
                f.write(linea)
                logging.info(f"[SCAN] Escribiendo bloque {bloque:03d} → {txn.transaction_id} ({txn.status.value})")


# ---------------------------------------------------------------------------
# Sección 4: Simulación principal
# ---------------------------------------------------------------------------

def crear_cuentas() -> dict:
    """Crea el conjunto inicial de cuentas bancarias."""
    cuentas_data = [
        ("ACC001", "Alice Gómez",    5_000.0),
        ("ACC002", "Bob Martínez",   3_000.0),
        ("ACC003", "Carol Herrera",  8_000.0),
        ("ACC004", "David Ríos",     1_500.0),
        ("ACC005", "Elena Vargas",  10_000.0),
    ]
    return {cid: Account(cid, nombre, saldo) for cid, nombre, saldo in cuentas_data}


def crear_transacciones_demo(cuentas: dict) -> list:
    """
    Construye un conjunto de transacciones de demostración que cubren
    todos los tipos y todos los roles definidos en el sistema.
    """
    ids_cuentas = list(cuentas.keys())
    transacciones = []

    # -- Depósitos (CAJERO y ADMINISTRADOR pueden hacerlos) --
    transacciones.append(
        TransactionBuilder("cajero01", "CAJERO")
        .with_deposit("ACC001", 1_000.0)
        .with_metadata("canal", "ventanilla")
        .build()
    )
    transacciones.append(
        TransactionBuilder("admin01", "ADMINISTRADOR")
        .with_deposit("ACC003", 500.0)
        .with_metadata("canal", "sistema")
        .build()
    )

    # -- Retiros (CAJERO y ADMINISTRADOR) --
    transacciones.append(
        TransactionBuilder("cajero01", "CAJERO")
        .with_withdrawal("ACC002", 200.0)
        .build()
    )
    transacciones.append(
        TransactionBuilder("cajero02", "CAJERO")
        .with_withdrawal("ACC004", 5_000.0)   # fallará: fondos insuficientes
        .build()
    )

    # -- Transferencias (sólo ADMINISTRADOR) --
    transacciones.append(
        TransactionBuilder("admin01", "ADMINISTRADOR")
        .with_transfer("ACC001", "ACC002", 300.0)
        .build()
    )
    transacciones.append(
        TransactionBuilder("admin01", "ADMINISTRADOR")
        .with_transfer("ACC005", "ACC004", 2_000.0)
        .build()
    )

    # -- Consultas (todos los roles) --
    transacciones.append(
        TransactionBuilder("auditor01", "AUDITOR")
        .with_query("ACC003")
        .build()
    )
    transacciones.append(
        TransactionBuilder("cajero01", "CAJERO")
        .with_query("ACC001")
        .build()
    )

    # -- Operaciones denegadas por RBAC --
    # AUDITOR intentando depósito → denegado
    transacciones.append(
        TransactionBuilder("auditor01", "AUDITOR")
        .with_deposit("ACC002", 100.0)
        .with_metadata("nota", "debe ser denegado por RBAC")
        .build()
    )
    # CAJERO intentando transferencia → denegado
    transacciones.append(
        TransactionBuilder("cajero02", "CAJERO")
        .with_transfer("ACC003", "ACC005", 500.0)
        .with_metadata("nota", "debe ser denegado por RBAC")
        .build()
    )

    # -- Carga aleatoria adicional --
    random.seed(42)
    roles_permitidos = ["CAJERO", "ADMINISTRADOR", "AUDITOR"]
    for i in range(10):
        cuenta_src = random.choice(ids_cuentas)
        rol = random.choice(roles_permitidos)
        tipo = random.choice(["deposito", "retiro", "consulta"])

        if tipo == "deposito":
            txn = TransactionBuilder(f"user{i}", rol).with_deposit(cuenta_src, random.uniform(50, 500)).build()
        elif tipo == "retiro":
            txn = TransactionBuilder(f"user{i}", rol).with_withdrawal(cuenta_src, random.uniform(10, 300)).build()
        else:
            txn = TransactionBuilder(f"user{i}", rol).with_query(cuenta_src).build()

        transacciones.append(txn)

    return transacciones


def imprimir_estado_cuentas(cuentas: dict):
    """Imprime el saldo final de todas las cuentas."""
    print("\n" + "="*60)
    print("  ESTADO FINAL DE CUENTAS")
    print("="*60)
    for cuenta in cuentas.values():
        print(f"  {cuenta}")
    print("="*60 + "\n")


def imprimir_resumen_resultados(resultados: list):
    """Imprime un resumen de los resultados de las transacciones."""
    from core.transaction import TransactionStatus
    completadas = sum(1 for r in resultados if r.status == TransactionStatus.COMPLETED)
    fallidas    = sum(1 for r in resultados if r.status == TransactionStatus.FAILED)
    denegadas   = sum(1 for r in resultados if r.status == TransactionStatus.DENIED)

    print("\n" + "="*60)
    print("  RESUMEN DE TRANSACCIONES")
    print("="*60)
    print(f"  Total procesadas : {len(resultados)}")
    print(f"  Completadas      : {completadas}")
    print(f"  Fallidas         : {fallidas}  (ej: fondos insuficientes)")
    print(f"  Denegadas        : {denegadas}  (RBAC o Banquero)")
    print("="*60)

    print("\n  Detalle:")
    for r in resultados:
        icono = "✓" if r.status.value == "COMPLETED" else "✗"
        print(f"  {icono} [{r.transaction_id}] {r.get_operation_summary()} "
              f"| rol={r.user_role} | {r.status.value}")
    print()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*60)
    print("  PROCESADOR DE TRANSACCIONES BANCARIAS")
    print("  Sistemas Operativos — UTP 2026-1")
    print("="*60 + "\n")

    # 1. Crear cuentas
    cuentas = crear_cuentas()
    logging.info(f"[MAIN] {len(cuentas)} cuentas inicializadas.")

    # 2. Inicializar política RBAC y construir el hook para el motor
    politica_rbac = PoliticaRBAC()
    hook_rbac     = construir_hook_rbac(politica_rbac)
    logging.info("[MAIN] Política RBAC cargada.")

    # 3. Inicializar Algoritmo del Banquero y construir el guard para el motor
    hook_banquero = construir_guard_banquero(cuentas)
    logging.info("[MAIN] Guardia Banquero inicializado.")

    # 4. Crear y arrancar el motor de transacciones
    motor = TransactionEngine(cuentas, max_concurrent=3, num_workers=3)
    motor.set_authorization_hook(hook_rbac)
    motor.set_bankers_guard(hook_banquero)
    motor.start()
    logging.info("[MAIN] Motor de transacciones iniciado.")

    # 5. Generar y someter transacciones
    transacciones = crear_transacciones_demo(cuentas)
    logging.info(f"[MAIN] Sometiendo {len(transacciones)} transacciones al motor...")

    for txn in transacciones:
        motor.submit_transaction(txn)

    # 6. Esperar a que todas las transacciones terminen
    motor.wait_completion()
    logging.info("[MAIN] Todas las transacciones han sido procesadas.")

    # 7. Recuperar resultados
    resultados = motor.get_all_results()

    # 8. Detener el motor
    motor.stop()
    logging.info("[MAIN] Motor detenido.")

    # 9. Ordenar y registrar resultados con SCAN
    logging.info("[MAIN] Iniciando escritura de log con planificación SCAN...")
    registrar_resultados_con_scan(resultados, archivo_log="banco-transacciones-so/logs/transactions.log")
    logging.info("[MAIN] Log escrito en logs/transactions.log")

    # 10. Mostrar resumen en consola
    imprimir_resumen_resultados(resultados)
    imprimir_estado_cuentas(cuentas)


if __name__ == "__main__":
    main()