"""
Core module for banco-transacciones-so.

Implements the heart of the banking transaction system with thread-safe account
management, transaction processing, and producer-consumer patterns.

Exports:
    Account: Thread-safe bank account with mutex synchronization
    Transaction: Transaction data model with lifecycle management
    TransactionType: Enum of transaction types (DEPOSIT, WITHDRAWAL, TRANSFER, QUERY)
    TransactionStatus: Enum of transaction states throughout lifecycle
    TransactionBuilder: Builder pattern for safe transaction construction
    TransactionEngine: Producer-consumer engine for concurrent transaction processing
"""

from .account import Account
from .transaction import (
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionBuilder
)
from .transaction_engine import TransactionEngine

__all__ = [
    'Account',
    'Transaction',
    'TransactionType',
    'TransactionStatus',
    'TransactionBuilder',
    'TransactionEngine',
]

__version__ = '1.0.0'
__author__ = 'Sistemas Operativos Team'
