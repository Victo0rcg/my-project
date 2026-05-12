"""
Module 1: Transaction Core
Defines core data structures and operations for the banking transaction system.
Provides Transaction class, TransactionType enum, and transaction-related utilities.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class TransactionType(Enum):
    """Types of banking transactions."""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    QUERY = "QUERY"


class TransactionStatus(Enum):
    """Status states for transactions throughout their lifecycle."""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"


@dataclass
class Transaction:
    """
    Represents a banking transaction.
    
    Encapsulates all information about a transaction including accounts involved,
    amount, authorization details, and lifecycle status. Supports all transaction
    types: deposits, withdrawals, transfers, and account queries.
    
    Attributes:
        transaction_id (str): Unique identifier assigned at build time by TransactionBuilder
        transaction_type (TransactionType): Type of operation (DEPOSIT, WITHDRAWAL, TRANSFER, QUERY)
        source_account_id (str): Account initiating the operation
        amount (float): Transaction amount
        user_id (str): User requesting the transaction
        user_role (str): Role of the requesting user (for RBAC authorization)
        destination_account_id (Optional[str]): Target account for transfers
        timestamp (Optional[datetime]): When the transaction was created
        block_number (int): Fictitious block number for SCAN scheduling
        status (str): Current status (PENDING, AUTHORIZED, PROCESSING, COMPLETED, FAILED, DENIED)
        description (str): Human-readable description of the transaction
        metadata (dict): Additional contextual information
    """
    transaction_id: str
    transaction_type: TransactionType
    source_account_id: str
    amount: float
    user_id: str
    user_role: str
    destination_account_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    block_number: int = 0
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values and validate transaction."""
        if self.timestamp is None:
            self.timestamp = datetime.now()       
        # Validate transaction consistency
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate transaction consistency and constraints.
        
        Raises:
            ValueError: If transaction violates constraints
        """
        if self.transaction_type != TransactionType.QUERY:
            if self.amount <= 0:
                raise ValueError(
                    f"Transaction amount must be positive, got {self.amount}"
                )
        
        if not self.transaction_id:
            raise ValueError("Transaction ID cannot be empty")
        
        if self.transaction_type == TransactionType.TRANSFER:
            if not self.destination_account_id:
                raise ValueError("Transfer transaction must have destination_account_id")
            if self.source_account_id == self.destination_account_id:
                raise ValueError("Source and destination accounts cannot be the same")
        
        if not isinstance(self.transaction_type, TransactionType):
            raise ValueError(f"Invalid transaction type: {self.transaction_type}")
    
    def mark_authorized(self) -> None:
        """Mark transaction as authorized by RBAC policy."""
        if self.status == TransactionStatus.PENDING:
            self.status = TransactionStatus.AUTHORIZED
            self.metadata['authorized_at'] = datetime.now().isoformat()
    
    def mark_processing(self) -> None:
        """Mark transaction as currently being processed."""
        if self.status in [TransactionStatus.AUTHORIZED, TransactionStatus.PENDING]:
            self.status = TransactionStatus.PROCESSING
            self.metadata['processing_started_at'] = datetime.now().isoformat()
    
    def mark_completed(self) -> None:
        """Mark transaction as successfully completed."""
        self.status = TransactionStatus.COMPLETED
        self.metadata['completed_at'] = datetime.now().isoformat()
    
    def mark_failed(self, reason: str = "") -> None:
        """
        Mark transaction as failed.
        
        Args:
            reason (str): Reason for failure
        """
        self.status = TransactionStatus.FAILED
        self.metadata['failed_at'] = datetime.now().isoformat()
        if reason:
            self.metadata['failure_reason'] = reason
    
    def mark_denied(self, reason: str = "Authorization denied") -> None:
        """
        Mark transaction as denied by authorization policy.
        
        Args:
            reason (str): Reason for denial
        """
        self.status = TransactionStatus.DENIED
        self.metadata['denied_at'] = datetime.now().isoformat()
        self.metadata['denial_reason'] = reason
    
    def get_operation_summary(self) -> str:
        """
        Get a human-readable summary of the transaction.
        
        Returns:
            str: Formatted transaction summary
        """
        if self.transaction_type == TransactionType.DEPOSIT:
            return f"Deposit ${self.amount:.2f} to {self.source_account_id}"
        elif self.transaction_type == TransactionType.WITHDRAWAL:
            return f"Withdraw ${self.amount:.2f} from {self.source_account_id}"
        elif self.transaction_type == TransactionType.TRANSFER:
            return (f"Transfer ${self.amount:.2f} from {self.source_account_id} "
                   f"to {self.destination_account_id}")
        elif self.transaction_type == TransactionType.QUERY:
            return f"Query balance of {self.source_account_id}"
        else:
            return f"Unknown operation type: {self.transaction_type}"
    
    def get_affected_accounts(self) -> list:
        """
        Get list of all accounts affected by this transaction.
        
        Returns:
            list: Account IDs involved in the transaction
        """
        accounts = [self.source_account_id]
        if self.destination_account_id and self.destination_account_id not in accounts:
            accounts.append(self.destination_account_id)
        return accounts
    
    def is_multi_account(self) -> bool:
        """
        Check if transaction involves multiple accounts.
        
        Returns:
            bool: True if transaction affects more than one account
        """
        return len(self.get_affected_accounts()) > 1
    
    def requires_authorization(self) -> bool:
        """
        Check if transaction requires RBAC authorization check.
        
        Returns:
            bool: True if transaction type requires authorization validation
        """
        # Query operations might not require authorization in some policies
        return self.transaction_type != TransactionType.QUERY
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Transaction(id={self.transaction_id}, type={self.transaction_type.value}, "
               f"from={self.source_account_id}, to={self.destination_account_id}, "
               f"amount=${self.amount:.2f}, status={self.status}, user={self.user_id})")
    
    def __str__(self) -> str:
        """Readable string representation."""
        return f"[{self.transaction_id}] {self.get_operation_summary()} - Status: {self.status}"
    
    def to_dict(self) -> dict:
        """
        Convert transaction to dictionary for serialization.
        
        Returns:
            dict: Transaction data as dictionary
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
        Create a Transaction from a dictionary.
        
        Args:
            data (dict): Dictionary containing transaction data
            
        Returns:
            Transaction: Reconstructed transaction object
        """
        data_copy = data.copy()
        
        # Convert string transaction_type back to enum
        if isinstance(data_copy.get('transaction_type'), str):
            data_copy['transaction_type'] = TransactionType(data_copy['transaction_type'])
        
        # Convert timestamp string back to datetime
        if isinstance(data_copy.get('timestamp'), str):
            data_copy['timestamp'] = datetime.fromisoformat(data_copy['timestamp'])
        
        return cls(**data_copy)


class TransactionBuilder:
    """
    Builder pattern for creating Transaction objects with validation.
    
    Provides a fluent interface for constructing transactions with required
    and optional parameters, ensuring all constraints are satisfied.
    """
    
    def __init__(self, transaction_id: str, user_id: str, user_role: str):
        """
        Initialize transaction builder with required parameters.
        
        Args:
            transaction_id (str): Unique transaction identifier
            user_id (str): User requesting the transaction
            user_role (str): User's role for RBAC
        """
        self._transaction_id = ""
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
        Configure as a deposit transaction.
        
        Args:
            account_id (str): Account to deposit into
            amount (float): Deposit amount
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._transaction_type = TransactionType.DEPOSIT
        self._source_account_id = account_id
        self._amount = amount
        self._description = f"Deposit ${amount:.2f}"
        return self
    
    def with_withdrawal(self, account_id: str, amount: float) -> 'TransactionBuilder':
        """
        Configure as a withdrawal transaction.
        
        Args:
            account_id (str): Account to withdraw from
            amount (float): Withdrawal amount
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._transaction_type = TransactionType.WITHDRAWAL
        self._source_account_id = account_id
        self._amount = amount
        self._description = f"Withdraw ${amount:.2f}"
        return self
    
    def with_transfer(self, source_id: str, destination_id: str, 
                     amount: float) -> 'TransactionBuilder':
        """
        Configure as a transfer transaction.
        
        Args:
            source_id (str): Source account ID
            destination_id (str): Destination account ID
            amount (float): Transfer amount
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._transaction_type = TransactionType.TRANSFER
        self._source_account_id = source_id
        self._destination_account_id = destination_id
        self._amount = amount
        self._description = f"Transfer ${amount:.2f} from {source_id} to {destination_id}"
        return self
    
    def with_query(self, account_id: str) -> 'TransactionBuilder':
        """
        Configure as a query transaction.
        
        Args:
            account_id (str): Account to query
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._transaction_type = TransactionType.QUERY
        self._source_account_id = account_id
        self._amount: Optional[float] = None
        self._description = f"Balance query for {account_id}"
        return self
    
    def with_block_number(self, block_number: int) -> 'TransactionBuilder':
        """
        Set the fictitious block number for SCAN scheduling.
        
        Args:
            block_number (int): Block number
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._block_number = block_number
        return self
    
    def with_metadata(self, key: str, value: Any) -> 'TransactionBuilder':
        """
        Add metadata key-value pair.
        
        Args:
            key (str): Metadata key
            value: Metadata value
            
        Returns:
            TransactionBuilder: Self for method chaining
        """
        self._metadata[key] = value
        return self
    
    def build(self) -> Transaction:
        """
        Build the Transaction object.
        
        Returns:
            Transaction: Constructed transaction
            
        Raises:
            ValueError: If required fields are not set
        """
        if self._transaction_type is None:
            raise ValueError("Transaction type must be set (use with_* methods)")
        
        if self._source_account_id is None:
            raise ValueError("Source account must be set")
        
        if self._transaction_type != TransactionType.QUERY and self._amount is None:
            raise ValueError("Amount must be set for non-query transactions")
        
        return Transaction(
            transaction_id=self._transaction_id,
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
