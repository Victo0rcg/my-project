import threading
import logging
import os
import json
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Account:
    account_id: str
    holder_name: str
    initial_balance: float = 0.0
    
    def __post_init__(self):
        self.balance = self.initial_balance
        self._lock = threading.Lock()
        self._transaction_history = []
        self._folder = "cuentas"
        os.makedirs(self._folder, exist_ok=True)
        self._file_path = os.path.join(self._folder, f"{self.account_id}.json")
        self._guardar_en_archivo_fisico()
    
    def _guardar_en_archivo_fisico(self):
        datos = {
            "account_id": self.account_id,
            "holder_name": self.holder_name,
            "balance": self.balance,
            "last_update": datetime.now().isoformat()
        }
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)

    def _leer_de_archivo_fisico(self):
        if os.path.exists(self._file_path):
            with open(self._file_path, "r", encoding="utf-8") as f:
                datos = json.load(f)
                self.balance = datos["balance"]

    def deposit(self, amount: float, description: str = "Deposit") -> bool:
        if amount <= 0:
            raise ValueError("Monto invalido.")
        logging.info(f"[CUENTA {self.account_id}] Proceso compitiendo. Solicitando MUTEX para operacion de ESCRITURA...")
        with self._lock:
            logging.info(f"[CUENTA {self.account_id}] MUTEX adquirido. Abriendo y modificando archivo fisico...")
            self._leer_de_archivo_fisico()
            previous_balance = self.balance
            self.balance += amount
            self._guardar_en_archivo_fisico()
            logging.info(f"[CUENTA {self.account_id}] Escritura exitosa. Saldo: ${previous_balance:.2f} -> ${self.balance:.2f}. Liberando MUTEX...")
            self._transaction_history.append({
                'type': 'DEPOSIT', 'amount': amount, 'previous_balance': previous_balance,
                'new_balance': self.balance, 'description': description,
                'timestamp': datetime.now().isoformat(), 'thread_id': threading.current_thread().ident
            })
            return True
    
    def withdraw(self, amount: float, description: str = "Withdrawal") -> bool:
        if amount <= 0:
            raise ValueError("Monto invalido.")
        logging.info(f"[CUENTA {self.account_id}] Proceso compitiendo. Solicitando MUTEX para operacion de ESCRITURA...")
        with self._lock:
            logging.info(f"[CUENTA {self.account_id}] MUTEX adquirido. Abriendo y modificando archivo fisico...")
            self._leer_de_archivo_fisico()
            if self.balance < amount:
                logging.warning(f"[CUENTA {self.account_id}] Fallo en escritura: Fondos insuficientes. Liberando MUTEX...")
                return False
            previous_balance = self.balance
            self.balance -= amount
            self._guardar_en_archivo_fisico()
            logging.info(f"[CUENTA {self.account_id}] Escritura exitosa. Saldo: ${previous_balance:.2f} -> ${self.balance:.2f}. Liberando MUTEX...")
            self._transaction_history.append({
                'type': 'WITHDRAWAL', 'amount': amount, 'previous_balance': previous_balance,
                'new_balance': self.balance, 'description': description,
                'timestamp': datetime.now().isoformat(), 'thread_id': threading.current_thread().ident
            })
            return True

    def get_balance(self) -> float:
        logging.info(f"[CUENTA {self.account_id}] Solicitando MUTEX para operacion de LECTURA de archivo...")
        with self._lock:
            logging.info(f"[CUENTA {self.account_id}] MUTEX adquirido para lectura. Accediendo al archivo de cuenta...")
            self._leer_de_archivo_fisico()
            return self.balance

    def get_history(self) -> list:
        with self._lock:
            return list(self._transaction_history)