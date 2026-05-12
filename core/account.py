"""
Module 1: Core Account Management
Implements thread-safe bank accounts with mutex synchronization.
"""

import threading
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Account:
    """
    Represents a bank account with thread-safe operations.
    
    Each account maintains its own Lock to ensure atomicity of operations
    like deposit, withdraw, and balance queries across concurrent threads.
    
    Attributes:
        account_id (str): Unique identifier for the account
        holder_name (str): Name of the account holder
        balance (float): Current account balance
        _lock (threading.Lock): Mutex for synchronizing access to balance
        _transaction_history (list): Record of all transactions
    """
    
    account_id: str
    holder_name: str
    initial_balance: float = 0.0
    
    def __post_init__(self):
        """Initialize the account with thread safety primitives."""
        self.balance = self.initial_balance
        self._lock = threading.Lock()
        self._transaction_history = []
        self._created_at = datetime.now()
    
    def deposit(self, amount: float, description: str = "Deposit") -> bool:
        """
        Deposit funds into the account (thread-safe).
        
        Acquires the mutex before modifying the balance, ensuring atomicity.
        Multiple threads can call this concurrently without race conditions.
        
        Args:
            amount (float): Amount to deposit (must be positive)
            description (str): Optional description of the deposit
            
        Returns:
            bool: True if successful, False if amount is invalid
            
        Raises:
            ValueError: If amount is negative or zero
        """
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive, got {amount}")
        
        with self._lock:
            previous_balance = self.balance
            self.balance += amount
            self._transaction_history.append({
                'type': 'DEPOSIT',
                'amount': amount,
                'previous_balance': previous_balance,
                'new_balance': self.balance,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'thread_id': threading.current_thread().ident
            })
            return True
    
    def withdraw(self, amount: float, description: str = "Withdrawal") -> bool:
        """
        Withdraw funds from the account (thread-safe).
        
        Acquires the mutex before modifying the balance. Prevents overdrafts
        by checking balance before withdrawing.
        
        Args:
            amount (float): Amount to withdraw (must be positive)
            description (str): Optional description of the withdrawal
            
        Returns:
            bool: True if successful, False if insufficient funds or invalid amount
            
        Raises:
            ValueError: If amount is negative or zero
        """
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive, got {amount}")
        
        with self._lock:
            if self.balance < amount:
                return False
            
            previous_balance = self.balance
            self.balance -= amount
            self._transaction_history.append({
                'type': 'WITHDRAWAL',
                'amount': amount,
                'previous_balance': previous_balance,
                'new_balance': self.balance,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'thread_id': threading.current_thread().ident
            })
            return True
    
    def get_balance(self) -> float:
        """
        Get the current account balance (thread-safe).
        
        Acquires the mutex to ensure a consistent snapshot of the balance.
        
        Returns:
            float: Current balance
        """
        with self._lock:
            return self.balance
    
        
    def transfer_internal(self, amount: float, source_id: str, 
                         description: str = "Transfer") -> bool:
        """
        Internal method to execute the balance change during transfer.
        
        Must be called while the account's lock is already held by the caller.
        Used by TransactionEngine after acquiring all necessary locks.
        
        Args:
            amount (float): Amount to debit or credit
            source_id (str): Source account ID (for outgoing transfer)
            description (str): Description of the transfer
            
        Returns:
            bool: True if successful
        """
        self.balance += amount  # amount is negative for outgoing, positive for incoming
        self._transaction_history.append({
            'type': 'TRANSFER',
            'amount': abs(amount),
            'direction': 'OUTGOING' if amount < 0 else 'INCOMING',
            'counterpart': source_id,
            'new_balance': self.balance,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'thread_id': threading.current_thread().ident
        })
        return True
    
    def can_transfer(self, amount: float) -> bool:
        """
        Check if account has sufficient funds for transfer (thread-safe).
        
        Acquires the mutex to ensure consistent balance check.
        
        Args:
            amount (float): Amount to check for transfer
            
        Returns:
            bool: True if sufficient funds available
        """
        if amount <= 0:
            return False
        
        with self._lock:
            return self.balance >= amount
    
    def get_transaction_history(self) -> list:
        """
        Retrieve the complete transaction history (thread-safe).
        
        Returns:
            list: Copy of transaction history to avoid external mutations
        """
        with self._lock:
            return self._transaction_history.copy()
    
    def acquire_lock(self):
        """Acquire the account's lock for external synchronization."""
        self._lock.acquire()

    def release_lock(self):
        """Release the account's lock for external synchronization."""
        self._lock.release()

    def __repr__(self) -> str:
        """String representation of the account."""
        return (f"Account(id={self.account_id}, holder={self.holder_name}, "
                f"balance=${self.balance:.2f})")
    
    def __str__(self) -> str:
        """Readable string representation."""
        return f"[{self.account_id}] {self.holder_name}: ${self.balance:.2f}"
