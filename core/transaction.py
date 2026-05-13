"""
Módulo 1: Núcleo de Transacciones
Define estructuras de datos nucleares y operaciones del sistema transaccional bancario.
Provee la clase Transaction, enumeración TransactionType y utilidades relacionadas.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class TransactionType(Enum):
    """Tipos de transacciones bancarias."""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    QUERY = "QUERY"


class TransactionStatus(Enum):
    """Estados de estatus de las transacciones durante su ciclo de vida."""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"


@dataclass
class Transaction:
    """
    Representa una transacción bancaria.
    
    Encapsula toda la información de una transacción incluyendo cuentas involucradas,
    cantidad, detalles de autorización y estado del ciclo de vida. Soporta todos los tipos
    de transacciones: depósitos, retiros, transferencias y consultas de cuenta.
    
    Atributos:
        transaction_id (str): Identificador único asignado en tiempo de construcción por TransactionBuilder
        transaction_type (TransactionType): Tipo de operación (DEPOSIT, WITHDRAWAL, TRANSFER, QUERY)
        source_account_id (str): Cuenta que inicia la operación
        amount (float): Cantidad de la transacción
        user_id (str): Usuario que solicita la transacción
        user_role (str): Rol del usuario solicitante (para autorización RBAC)
        destination_account_id (Optional[str]): Cuenta destino para transferencias
        timestamp (Optional[datetime]): Cuándo se creó la transacción
        block_number (int): Número de bloque ficticio para planificación SCAN
        status (str): Estado actual (PENDING, AUTHORIZED, PROCESSING, COMPLETED, FAILED, DENIED)
        description (str): Descripción legible de la transacción
        metadata (dict): Información contextual adicional
    """
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
        """Inicializa valores por defecto y valida la transacción."""
        if self.timestamp is None:
            self.timestamp = datetime.now()       
        # Valida consistencia de la transacción
        self._validate()
    
    def _validate(self) -> None:
        """
        Valida consistencia y restricciones de la transacción.
        
        Levanta:
            ValueError: Si la transacción viola restricciones
        """
        if self.transaction_type != TransactionType.QUERY:
            if self.amount <= 0:
                raise ValueError(
                    f"La cantidad de la transacción debe ser positiva, se obtuvo {self.amount}"
                )
                    
        if self.transaction_type == TransactionType.TRANSFER:
            if not self.destination_account_id:
                raise ValueError("La transacción de transferencia debe tener destination_account_id")
            if self.source_account_id == self.destination_account_id:
                raise ValueError("Las cuentas de origen y destino no pueden ser iguales")
        
        if not isinstance(self.transaction_type, TransactionType):
            raise ValueError(f"Tipo de transacción inválido: {self.transaction_type}")
    
    def mark_authorized(self) -> None:
        """Marca la transacción como autorizada por la política RBAC."""
        if self.status == TransactionStatus.PENDING:
            self.status = TransactionStatus.AUTHORIZED
            self.metadata['authorized_at'] = datetime.now().isoformat()
    
    def mark_processing(self) -> None:
        """Marca la transacción como actualmente en procesamiento."""
        if self.status in [TransactionStatus.AUTHORIZED, TransactionStatus.PENDING]:
            self.status = TransactionStatus.PROCESSING
            self.metadata['processing_started_at'] = datetime.now().isoformat()
    
    def mark_completed(self) -> None:
        """Marca la transacción como completada exitosamente."""
        self.status = TransactionStatus.COMPLETED
        self.metadata['completed_at'] = datetime.now().isoformat()
    
    def mark_failed(self, reason: str = "") -> None:
        """
        Marca la transacción como fallida.
        
        Argumentos:
            reason (str): Razón del fallo
        """
        self.status = TransactionStatus.FAILED
        self.metadata['failed_at'] = datetime.now().isoformat()
        if reason:
            self.metadata['failure_reason'] = reason
    
    def mark_denied(self, reason: str = "Autorización denegada") -> None:
        """
        Marca la transacción como denegada por la política de autorización.
        
        Argumentos:
            reason (str): Razón de la denegación
        """
        self.status = TransactionStatus.DENIED
        self.metadata['denied_at'] = datetime.now().isoformat()
        self.metadata['denial_reason'] = reason
    
    def get_operation_summary(self) -> str:
        """
        Obtiene un resumen legible de la transacción.
        
        Retorna:
            str: Resumen de la transacción formateado
        """
        if self.transaction_type == TransactionType.DEPOSIT:
            return f"Depósito ${self.amount:.2f} en {self.source_account_id}"
        elif self.transaction_type == TransactionType.WITHDRAWAL:
            return f"Retiro ${self.amount:.2f} de {self.source_account_id}"
        elif self.transaction_type == TransactionType.TRANSFER:
            return (f"Transferencia ${self.amount:.2f} de {self.source_account_id} "
                   f"a {self.destination_account_id}")
        elif self.transaction_type == TransactionType.QUERY:
            return f"Consulta de saldo de {self.source_account_id}"
        else:
            return f"Tipo de operación desconocido: {self.transaction_type}"
    
    def get_affected_accounts(self) -> list:
        """
        Obtiene lista de todas las cuentas afectadas por esta transacción.
        
        Retorna:
            list: Identificadores de cuentas involucradas en la transacción
        """
        accounts = [self.source_account_id]
        if self.destination_account_id and self.destination_account_id not in accounts:
            accounts.append(self.destination_account_id)
        return accounts
    
    def is_multi_account(self) -> bool:
        """
        Verifica si la transacción involucra múltiples cuentas.
        
        Retorna:
            bool: Verdadero si la transacción afecta más de una cuenta
        """
        return len(self.get_affected_accounts()) > 1
    
    def requires_authorization(self) -> bool:
        """
        Verifica si la transacción requiere verificación de autorización RBAC.
        
        Retorna:
            bool: Verdadero si el tipo de transacción requiere validación de autorización
        """
        # Las operaciones de consulta podrían no requerir autorización en algunas políticas
        return self.transaction_type != TransactionType.QUERY
    
    def __repr__(self) -> str:
        """Representación de cadena detallada para depuración."""
        return (f"Transaction(id={self.transaction_id}, type={self.transaction_type.value}, "
               f"from={self.source_account_id}, to={self.destination_account_id}, "
               f"amount=${self.amount:.2f}, status={self.status}, user={self.user_id})")
    
    def __str__(self) -> str:
        """Representación de cadena legible."""
        return f"[{self.transaction_id}] {self.get_operation_summary()} - Estado: {self.status}"
    
    def to_dict(self) -> dict:
        """
        Convierte la transacción a diccionario para serialización.
        
        Retorna:
            dict: Datos de la transacción como diccionario
        """
        return {
            'transaction_id': self.transaction_id,
            'transaction_type': self.transaction_type.value,
            'source_account_id': self.source_account_id,
            'destination_account_id': self.destination_account_id,
            'amount': self.amount,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'block_number': self.block_number,
            'status': self.status.value,
            'description': self.description,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """
        Crea una Transaction a partir de un diccionario.
        
        Argumentos:
            data (dict): Diccionario que contiene datos de la transacción
            
        Retorna:
            Transaction: Objeto de transacción reconstruido
        """
        data_copy = data.copy()
        
        # Convierte cadena de transaction_type nuevamente a enumeración
        if isinstance(data_copy.get('transaction_type'), str):
            data_copy['transaction_type'] = TransactionType(data_copy['transaction_type'])
        
        # Convierte cadena de timestamp nuevamente a datetime
        if isinstance(data_copy.get('timestamp'), str):
            data_copy['timestamp'] = datetime.fromisoformat(data_copy['timestamp'])
        
        return cls(**data_copy)


class TransactionBuilder:
    """
    Patrón Builder para crear objetos Transaction con validación.
    
    Proporciona una interfaz fluida para construir transacciones con parámetros
    requeridos y opcionales, asegurando que se cumplan todas las restricciones.
    """
    
    def __init__(self, user_id: str, user_role: str):
        """
        Inicializa el constructor de transacciones con parámetros requeridos.
        
        Argumentos:
            transaction_id (str): Identificador único de la transacción
            user_id (str): Usuario que solicita la transacción
            user_role (str): Rol del usuario para RBAC
        """
        self._transaction_id = None
        self._user_id = user_id
        self._user_role = user_role
        self._transaction_type: Optional[TransactionType] = None
        self._source_account_id: Optional[str] = None
        self._destination_account_id: Optional[str] = None
        self._amount: Optional[float] = None
        self._block_number: int = 0
        self._description: str = ""
        self._metadata: dict = {}
    
    def with_deposit(self, account_id: str, amount: float) -> 'TransactionBuilder':
        """
        Configura como transacción de depósito.
        
        Argumentos:
            account_id (str): Cuenta donde hacer el depósito
            amount (float): Cantidad del depósito
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._transaction_type = TransactionType.DEPOSIT
        self._source_account_id = account_id
        self._amount = amount
        self._description = f"Depósito ${amount:.2f}"
        return self
    
    def with_withdrawal(self, account_id: str, amount: float) -> 'TransactionBuilder':
        """
        Configura como transacción de retiro.
        
        Argumentos:
            account_id (str): Cuenta de donde hacer el retiro
            amount (float): Cantidad del retiro
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._transaction_type = TransactionType.WITHDRAWAL
        self._source_account_id = account_id
        self._amount = amount
        self._description = f"Retiro ${amount:.2f}"
        return self
    
    def with_transfer(self, source_id: str, destination_id: str, 
                     amount: float) -> 'TransactionBuilder':
        """
        Configura como transacción de transferencia.
        
        Argumentos:
            source_id (str): Identificador de cuenta origen
            destination_id (str): Identificador de cuenta destino
            amount (float): Cantidad de transferencia
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._transaction_type = TransactionType.TRANSFER
        self._source_account_id = source_id
        self._destination_account_id = destination_id
        self._amount = amount
        self._description = f"Transferencia ${amount:.2f} de {source_id} a {destination_id}"
        return self
    
    def with_query(self, account_id: str) -> 'TransactionBuilder':
        """
        Configura como transacción de consulta.
        
        Argumentos:
            account_id (str): Cuenta a consultar
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._transaction_type = TransactionType.QUERY
        self._source_account_id = account_id
        self._amount: Optional[float] = None
        self._description = f"Consulta de saldo para {account_id}"
        return self
    
    def with_block_number(self, block_number: int) -> 'TransactionBuilder':
        """
        Establece el número de bloque ficticio para planificación SCAN.
        
        Argumentos:
            block_number (int): Número de bloque
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._block_number = block_number
        return self
    
    def with_metadata(self, key: str, value: Any) -> 'TransactionBuilder':
        """
        Agrega un par clave-valor de metadatos.
        
        Argumentos:
            key (str): Clave de metadatos
            value: Valor de metadatos
            
        Retorna:
            TransactionBuilder: A sí mismo para encadenamiento de métodos
        """
        self._metadata[key] = value
        return self
    
    def build(self) -> Transaction:
        """
        Construye el objeto Transaction.
        
        Retorna:
            Transaction: Transacción construida
            
        Levanta:
            ValueError: Si los campos requeridos no están establecidos
        """
        if self._transaction_type is None:
            raise ValueError("El tipo de transacción debe establecerse (use métodos with_*)")
        
        if self._source_account_id is None:
            raise ValueError("La cuenta de origen debe estar establecida")
        
        if self._transaction_type != TransactionType.QUERY and self._amount is None:
            raise ValueError("La cantidad debe establecerse para transacciones que no sean consultas")
        
        return Transaction(
            transaction_type=self._transaction_type,
            source_account_id=self._source_account_id,
            destination_account_id=self._destination_account_id,
            amount=self._amount or 0.0,
            user_id=self._user_id,
            user_role=self._user_role,
            block_number=self._block_number,
            description=self._description,
            metadata=self._metadata.copy()
        )
