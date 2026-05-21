import logging
import threading
import queue
import random
import time
from datetime import datetime
from typing import Dict, Optional, Callable, TYPE_CHECKING
from .transaction import Transaction, TransactionType, TransactionStatus

if TYPE_CHECKING:
    from .account import Account

class TransactionEngine:
    def __init__(self, accounts: Dict[str, 'Account'], max_concurrent: int = 5, num_workers: int = 3):
        self._transaction_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._accounts = accounts
        self._max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._num_workers = num_workers
        self._workers = []
        self._running = False
        self._lock = threading.Lock()
        self._transaction_counter = 0
        self._authorization_hook: Optional[Callable] = None
        self._bankers_guard: Optional[Callable] = None
    
    def set_authorization_hook(self, hook: Callable) -> None:
        self._authorization_hook = hook
    
    def set_bankers_guard(self, guard: Callable) -> None:
        self._bankers_guard = guard

    def _ejecutar_rutina_interrupcion(self, tipo_interrupcion: str, detalle: str):
        logging.warning(f"[ISR] -> ATENDIENDO INTERRUPCION DE LINEA: {tipo_interrupcion}")
        logging.warning(f"[ISR] -> Detalle del Vector de Interrupcion: {detalle}")
        logging.warning(f"[ISR] -> Cambiando contexto de CPU. Salvando registros en pila...")
        time.sleep(0.3)
        logging.info(f"[ISR] -> Interrupcion resuelta con exito. Retornando el control al planificador de procesos.")

    def start(self) -> None:
        with self._lock:
            if self._running:
                raise RuntimeError("El motor ya esta activo.")
            self._running = True
        logging.info(f"[MOTOR] Desplegando {self._num_workers} Hilos Workers para procesamiento concurrente...")
        for i in range(self._num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"Worker-{i+1}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
    
    def stop(self, timeout: float = 5.0) -> None:
        logging.info("[MOTOR] Solicitando detencion de hilos activos...")
        with self._lock:
            self._running = False
        for _ in self._workers:
            self._transaction_queue.put(None)
        for worker in self._workers:
            worker.join(timeout=timeout)
        self._workers.clear()
        logging.info("[MOTOR] Hilos de procesamiento finalizados.")
    
    def submit_transaction(self, transaction: Transaction) -> str:
        if not self._running:
            raise RuntimeError("Motor apagado.")
        with self._lock:
            self._transaction_counter += 1
            transaction.transaction_id = f"TX-{self._transaction_counter:04d}"
        transaction.block_number = random.randint(1, 199)
        logging.info(f"[MOTOR] Transaccion {transaction.transaction_id} recibida. Destinada a sector de disco: {transaction.block_number}")
        self._transaction_queue.put(transaction)
        return transaction.transaction_id
    
    def _worker_loop(self) -> None:
        while True:
            transaction = self._transaction_queue.get()
            if transaction is None:
                self._transaction_queue.task_done()
                break
            logging.info(f"[MOTOR] Hilo despachador toma {transaction.transaction_id}")
            transaction.mark_processing()

            if random.random() < 0.15:
                logging.warning(f"[HARDWARE] ! ALERTA ! Linea IRQ-03 activada de forma asincrona.")
                self._ejecutar_rutina_interrupcion("IRQ-03 (Fallo Temporal de Linea de Comunicacion)", f"Afecto el procesamiento de la {transaction.transaction_id}")

            if self._authorization_hook and not self._authorization_hook(transaction):
                logging.warning(f"[SOFTWARE] ! TRAP DE SEGURIDAD DETECTADO ! Violacion de politicas de acceso.")
                transaction.mark_denied("Rechazado por el subsistema de archivos de seguridad RBAC.")
                self._ejecutar_rutina_interrupcion("TRAP-01 (Acceso No Autorizado Extricto)", f"Usuario con Rol no valido intento modificar archivo de cuenta en {transaction.transaction_id}")
                self._result_queue.put(transaction)
                self._transaction_queue.task_done()
                continue

            if self._bankers_guard and not self._bankers_guard(transaction):
                logging.warning(f"[SOFTWARE] ! TRAP DE CONCURRENCIA DETECTADO ! Estado Inseguro de Recursos.")
                transaction.mark_denied("Rechazado por el planificador de prevencion de interbloqueos.")
                self._ejecutar_rutina_interrupcion("TRAP-02 (Riesgo de Bloqueo Mutuo)", f"El algoritmo del banquero aborto preventivamente el proceso para evitar un Deadlock")
                self._result_queue.put(transaction)
                self._transaction_queue.task_done()
                continue

            logging.info(f"[MOTOR] {transaction.transaction_id} solicitando ranura en el Semaforo de multiprocesamiento...")
            with self._semaphore:
                logging.info(f"[MOTOR] {transaction.transaction_id} dentro de la seccion critica de hardware.")
                try:
                    self._execute_transaction(transaction)
                    time.sleep(0.2)
                except Exception as e:
                    logging.error(f"[MOTOR] Excepcion en {transaction.transaction_id}: {str(e)}")
                    transaction.mark_failed(str(e))
            logging.info(f"[MOTOR] {transaction.transaction_id} libero el semaforo central. Estado: {transaction.status.name}")
            self._result_queue.put(transaction)
            self._transaction_queue.task_done()

    def _execute_transaction(self, transaction: Transaction) -> None:
        src_id = transaction.source_account_id
        dest_id = transaction.destination_account_id
        if src_id not in self._accounts:
            transaction.mark_failed("Archivo de cuenta origen no encontrado.")
            return
        source_account = self._accounts[src_id]
        logging.info(f"[MOTOR] Exec: {transaction.get_operation_summary()}")

        if transaction.transaction_type == TransactionType.QUERY:
            transaction.description = f"Lectura de archivo exitosa. Balance actual: ${source_account.get_balance():.2f}"
            transaction.mark_completed()
        elif transaction.transaction_type == TransactionType.DEPOSIT:
            if source_account.deposit(transaction.amount, f"Modificacion por {transaction.user_id}"):
                transaction.mark_completed()
            else:
                transaction.mark_failed("Fallo al escribir deposito.")
        elif transaction.transaction_type == TransactionType.WITHDRAWAL:
            if source_account.withdraw(transaction.amount, f"Modificacion por {transaction.user_id}"):
                transaction.mark_completed()
            else:
                transaction.mark_failed("Fallo al escribir retiro.")
        elif transaction.transaction_type == TransactionType.TRANSFER:
            if dest_id not in self._accounts:
                transaction.mark_failed("Archivo de cuenta destino no encontrado.")
                return
            dest_account = self._accounts[dest_id]
            primera, segunda = (source_account, dest_account) if src_id < dest_id else (dest_account, source_account)
            logging.info(f"[MOTOR] Jerarquia de Locks activada para transferencia para evitar interbloqueo: {primera.account_id} -> {segunda.account_id}")
            with primera._lock:
                with segunda._lock:
                    source_account._leer_de_archivo_fisico()
                    if source_account.balance >= transaction.amount:
                        source_account.balance -= transaction.amount
                        dest_account.balance += transaction.amount
                        source_account._guardar_en_archivo_fisico()
                        dest_account._guardar_en_archivo_fisico()
                        tiempo = datetime.now().isoformat()
                        hilo = threading.current_thread().ident
                        source_account._transaction_history.append({
                            'type': 'TRANSFER_OUT', 'amount': transaction.amount,
                            'new_balance': source_account.balance, 'description': f"Escritura hacia {dest_id}",
                            'timestamp': tiempo, 'thread_id': hilo
                        })
                        dest_account._transaction_history.append({
                            'type': 'TRANSFER_IN', 'amount': transaction.amount,
                            'new_balance': dest_account.balance, 'description': f"Escritura desde {src_id}",
                            'timestamp': tiempo, 'thread_id': hilo
                        })
                        transaction.mark_completed()
                        logging.info("[MOTOR] Operacion de transferencia modificada en ambos archivos fisicos.")
                    else:
                        transaction.mark_failed("Fondos insuficientes al validar archivo origen.")