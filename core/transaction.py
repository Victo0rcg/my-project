from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    QUERY = "QUERY"

class TransactionStatus(Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"

@dataclass
class Transaction:
    source_account_id: str
    amount: float
    user_id: str
    user_role: str
    transaction_type: TransactionType
    transaction_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    block_number: int = 0
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()       
        self._validate()
    
    def _validate(self) -> None:
        if self.transaction_type != TransactionType.QUERY and self.amount <= 0:
            raise ValueError("Monto inváldo.")
        if self.transaction_type == TransactionType.TRANSFER:
            if not self.destination_account_id:
                raise ValueError("Falta destino.")
            if self.source_account_id == self.destination_account_id:
                raise ValueError("Cuentas idénticas.")
    
    def _mutar_estado(self, nuevo_estado: TransactionStatus, llave_tiempo: str, razon: str = "") -> None:
        self.status = nuevo_estado
        self.metadata[llave_tiempo] = datetime.now().isoformat()
        if razon:
            self.metadata["razon_estado"] = razon

    def mark_authorized(self) -> None:
        if self.status == TransactionStatus.PENDING:
            self._mutar_estado(TransactionStatus.AUTHORIZED, 'authorized_at')
    
    def mark_processing(self) -> None:
        if self.status in [TransactionStatus.AUTHORIZED, TransactionStatus.PENDING]:
            self._mutar_estado(TransactionStatus.PROCESSING, 'processing_started_at')
    
    def mark_completed(self) -> None:
        self._mutar_estado(TransactionStatus.COMPLETED, 'completed_at')
    
    def mark_failed(self, reason: str = "") -> None:
        self._mutar_estado(TransactionStatus.FAILED, 'failed_at', reason)
    
    def mark_denied(self, reason: str = "Autorización denegada") -> None:
        self._mutar_estado(TransactionStatus.DENIED, 'denied_at', reason)
    
    def get_operation_summary(self) -> str:
        if self.transaction_type == TransactionType.DEPOSIT:
            return f"Depósito de ${self.amount:.2f} en archivo de {self.source_account_id}"
        elif self.transaction_type == TransactionType.WITHDRAWAL:
            return f"Retiro de ${self.amount:.2f} desde archivo de {self.source_account_id}"
        elif self.transaction_type == TransactionType.TRANSFER:
            return f"Transferencia de ${self.amount:.2f} desde archivo {self.source_account_id} hacia {self.destination_account_id}"
        elif self.transaction_type == TransactionType.QUERY:
            return f"Lectura de archivo de balance de {self.source_account_id}"
        return "Desconocida"

    def to_dict(self) -> dict:
        return {
            'transaction_id': self.transaction_id,
            'transaction_type': self.transaction_type.value,
            'source_account_id': self.source_account_id,
            'destination_account_id': self.destination_account_id,
            'amount': self.amount,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'status': self.status.value,
            'block_number': self.block_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'description': self.description,
            'metadata': self.metadata
        }