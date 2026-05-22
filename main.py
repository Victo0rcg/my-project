import logging
import threading
import os
import sys
import time

from core.account import Account
from core.transaction import Transaction, TransactionType
from core.transaction_engine import TransactionEngine
from scheduling.scan_scheduler import scan_scheduling
from security.roles import Rol, Operacion
from security.rbac_policy import PoliticaRBAC
from concurrency.bankers_guard import GuardiaBanquero

_LOG_TRANSACTIONS = "logs/transactions.log"
os.makedirs("logs", exist_ok=True)

handlers = [
    logging.StreamHandler(sys.stdout)
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=handlers
)

_TIPO_A_OPERACION = {
    TransactionType.DEPOSIT:    Operacion.DEPOSITO,
    TransactionType.WITHDRAWAL: Operacion.RETIRO,
    TransactionType.TRANSFER:   Operacion.TRANSFERENCIA,
    TransactionType.QUERY:      Operacion.CONSULTA,
}

historico_procesadas = []
lock_historico = threading.Lock()

def construir_hook_rbac(politica: PoliticaRBAC):
    def hook(transaction: Transaction) -> bool:
        try:
            rol = Rol(transaction.user_role)
        except ValueError:
            logging.error(f"[RBAC] Estructura de rol no identificada: '{transaction.user_role}'")
            return False
        operacion = _TIPO_A_OPERACION.get(transaction.transaction_type)
        if operacion is None:
            return False
        return politica.verificar_permiso(rol, operacion)
    return hook

def construir_guard_banquero(cuentas: dict):
    n = len(cuentas)
    cuenta_ids = list(cuentas.keys())
    indice_cuenta = {cid: i for i, cid in enumerate(cuenta_ids)}
    recursos_disponibles  = [n]
    necesidad_maxima      = [[1]] * n
    recursos_asignados    = [[0]] * n
    guard = GuardiaBanquero(recursos_disponibles, necesidad_maxima, recursos_asignados)
    lock_guard = threading.Lock()

    def bankers_hook(transaction: Transaction) -> bool:
        if transaction.transaction_type != TransactionType.TRANSFER:
            return True
        idx = indice_cuenta.get(transaction.source_account_id)
        if idx is None:
            return True
        with lock_guard:
            try:
                aprobado = guard.solicitar_recursos(idx, [1])
                if aprobado:
                    guard.liberar_recursos(idx, [1])
                return aprobado
            except ValueError as e:
                logging.warning(f"[BANQUERO] Excepcion en validacion de seguridad: {e}")
                return False
    return bankers_hook

def registrar_resultados_con_scan(resultados: list, archivo_log: str = _LOG_TRANSACTIONS):
    print("\n" + "="*70)
    print(" SCAN - PLANIFICACION DE DISCO HARDWARE")
    print("="*70)
    if not resultados:
        print("[SCAN] No hay registros en la cola del brazo del disco.")
        return
    bloques = [t.block_number for t in resultados]
    posicion_inicial_cabeza = 50
    orden_bloques = scan_scheduling(bloques, posicion_inicial_cabeza, direction='up')
    transacciones_ordenadas = []
    resultados_copia = resultados.copy()
    for b in orden_bloques:
        for t in resultados_copia:
            if t.block_number == b:
                transacciones_ordenadas.append(t)
                resultados_copia.remove(t)
                break
    transacciones_ordenadas.extend(resultados_copia)

    with open(archivo_log, "w", encoding="utf-8") as f:
        f.write(f"=== REPORTE SCAN LOGS ===\n")
        print("\n ORDEN HISTORICO DE ESCRITURA FISICA EN DISCO LOG:")
        for t in transacciones_ordenadas:
            res_dict = t.to_dict()
            linea = (f" -> [Sector: {res_dict['block_number']:03d}] ID: {res_dict['transaction_id']} | "
                     f"Tipo: {res_dict['transaction_type']:<12} | Rol: {res_dict['user_role']:<14} | "
                     f"Estado: {res_dict['status']}")
            print(linea)
            f.write(linea + "\n")
    print(f"\n[SCAN] Logs sincronizados secuencialmente en: '{archivo_log}'")

def recolector_de_resultados(engine: TransactionEngine):
    while True:
        try:
            tx_procesada = engine._result_queue.get(timeout=1)
            if tx_procesada is None:
                break
            with lock_historico:
                historico_procesadas.append(tx_procesada)
            engine._result_queue.task_done()
        except Exception:
            continue

if __name__ == "__main__":
    cuentas_simuladas = {
        "ACC-001": Account("ACC-001", "Santiago", 5000.0),
        "ACC-002": Account("ACC-002", "Valeria", 3000.0),
        "ACC-003": Account("ACC-003", "Carlos", 1500.0)
    }
    politica = PoliticaRBAC()
    hook_rbac = construir_hook_rbac(politica)
    hook_banquero = construir_guard_banquero(cuentas_simuladas)
    engine = TransactionEngine(cuentas_simuladas, max_concurrent=2, num_workers=4)
    engine.set_authorization_hook(hook_rbac)
    engine.set_bankers_guard(hook_banquero)
    engine.start()
    hilo_recolector = threading.Thread(target=recolector_de_resultados, args=(engine,), name="Recolector", daemon=True)
    hilo_recolector.start()
    time.sleep(0.5)

    while True:
        print("\n" + "-"*70)
        print(" SIMULADOR DE SISTEMAS OPERATIVOS - MENU INTERACTIVO")
        print("-"*70)
        print(" 1. Ejecutar Rafaga Masiva (Demostrar Competencia Critica por Mutex)")
        print(" 2. Crear e Inyectar Transaccion Manual (Validacion RBAC)")
        print(" 3. Inspeccionar Saldo e Integridad de Archivos de Cuentas")
        print(" 4. Forzar Planificacion de Disco (SCAN Scheduler)")
        print(" 5. Apagar Motor y Salir")
        print("-"*70)
        opcion = input("Seleccione opcion (1-5): ").strip()
        
        if opcion == "1":
            print("\n LANZANDO PROCESOS EN PARALELO CONTRA LA CUENTA ACC-001 PARA FORZAR BLOQUEOS MUTEX...\n")
            cargas = [
                Transaction("ACC-001", 100.0, "Santiago", "ADMINISTRADOR", TransactionType.WITHDRAWAL),
                Transaction("ACC-001", 200.0, "Valeria", "CAJERO", TransactionType.DEPOSIT),
                Transaction("ACC-001", 150.0, "Santiago", "ADMINISTRADOR", TransactionType.WITHDRAWAL),
                Transaction("ACC-003", 0.0, "Carlos", "AUDITOR", TransactionType.QUERY),
                Transaction("ACC-003", 900.0, "Carlos", "AUDITOR", TransactionType.WITHDRAWAL),
                Transaction("ACC-001", 500.0, "Santiago", "ADMINISTRADOR", TransactionType.TRANSFER, destination_account_id="ACC-002")
            ]
            for tx in cargas:
                engine.submit_transaction(tx)
            time.sleep(2.0)
        elif opcion == "2":
            print("\n CONFIGURACION DE NUEVA TRANSACCION MANUAL:")
            src = input(" -> ID Cuenta Origen (ACC-001/ACC-002/ACC-003): ").strip().upper()
            if src not in cuentas_simuladas:
                print(" Cuenta no registrada.")
                continue
            rol_input = input(" -> Rol (ADMINISTRADOR/CAJERO/AUDITOR): ").strip().upper()
            print(" 1=DEPOSITO, 2=RETIRO, 3=TRANSFERENCIA, 4=CONSULTA")
            tipo_sel = input(" -> Seleccion de Tipo (1-4): ").strip()
            dest = None
            monto = 0.0
            if tipo_sel == "1": tipo_tx = TransactionType.DEPOSIT
            elif tipo_sel == "2": tipo_tx = TransactionType.WITHDRAWAL
            elif tipo_sel == "3": 
                tipo_tx = TransactionType.TRANSFER
                dest = input(" -> ID Cuenta Destino: ").strip().upper()
                if dest not in cuentas_simuladas:
                    print(" Cuenta destino inexistente.")
                    continue
            elif tipo_sel == "4": tipo_tx = TransactionType.QUERY
            else:
                print(" Opcion invalida.")
                continue
            if tipo_tx != TransactionType.QUERY:
                try:
                    monto = float(input(" -> Monto ($): "))
                except ValueError:
                    print(" Monto invalido numericamente.")
                    continue
            try:
                nueva_tx = Transaction(
                    source_account_id=src,
                    amount=monto,
                    user_id=f"User-{rol_input[:3]}",
                    user_role=rol_input,
                    transaction_type=tipo_tx,
                    destination_account_id=dest
                )
                engine.submit_transaction(nueva_tx)
                time.sleep(1.2)
            except Exception as e:
                print(f" Error de validacion estructural: {e}")
        elif opcion == "3":
            print("\n" + "-"*60)
            print(" ESTADO DE LOS ARCHIVOS FISICOS DE LAS CUENTAS (.json)")
            print("-"*60)
            for cid, acc in cuentas_simuladas.items():
                print(f" Archivo: cuentas/{cid}.json | Balance Escrito: ${acc.get_balance():.2f}")
            print("-"*60)
        elif opcion == "4":
            with lock_historico:
                copia_procesadas = list(historico_procesadas)
            registrar_resultados_con_scan(copia_procesadas)
        elif opcion == "5":
            print("\n Deteniendo los hilos del simulador...")
            engine.stop()
            engine._result_queue.put(None)
            hilo_recolector.join()
            with lock_historico:
                final_copia = list(historico_procesadas)
            registrar_resultados_con_scan(final_copia)
            print("\n[SISTEMA] El simulador de hardware se ha apagado.")
            break
        else:
            print(" Opcion invalida.")