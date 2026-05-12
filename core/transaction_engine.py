"""
Module 1: Transaction Engine
Implements a producer-consumer pattern for concurrent transaction processing
with thread-safe queue management and semaphore-based concurrency control.
"""

import logging
import threading
import queue
from typing import Dict, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from .transaction import (Transaction, TransactionType, TransactionStatus)

if TYPE_CHECKING:
    from .account import Account


class TransactionEngine:
    """
    Producer-consumer engine for processing concurrent transactions.
    
    Manages a thread-safe queue of transactions with semaphore-based concurrency
    control. Coordinates between transaction producers (application threads) and
    consumers (worker threads that execute transactions against accounts).
    
    Attributes:
        _transaction_queue (queue.Queue): Thread-safe buffer for pending transactions
        _result_queue (queue.Queue): Thread-safe buffer for completed transactions
        _accounts (dict): Dictionary mapping account IDs to Account objects
        _max_concurrent (int): Maximum concurrent transactions via semaphore
        _semaphore (threading.Semaphore): Limits concurrent transaction execution
        _workers (list): List of worker threads
        _running (bool): Flag to control engine operation
        _lock (threading.Lock): Protects engine state
        _transaction_counter (int): Auto-increment counter for transaction IDs
        _authorization_hook (Callable): Optional RBAC authorization callback
        _bankers_guard (Callable): Optional deadlock prevention callback
    """
    
    def __init__(self, accounts: Dict[str, 'Account'], 
                 max_concurrent: int = 5,
                 num_workers: int = 3):
        """
        Initialize the transaction engine.
        
        Args:
            accounts (dict): Dictionary of Account objects by account_id
            max_concurrent (int): Maximum concurrent transactions (default: 5)
            num_workers (int): Number of worker threads (default: 3)
        """
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
        """
        Set the RBAC authorization callback.
        
        Args:
            hook (callable): Function that validates transaction authorization
                            Signature: hook(transaction: Transaction) -> bool
        """
        self._authorization_hook = hook
    
    def set_bankers_guard(self, guard: Callable) -> None:
        """
        Set the deadlock prevention callback (Banker's Algorithm).
        
        Args:
            guard (callable): Function that validates deadlock-free state
                             Signature: guard(transaction: Transaction) -> bool
        """
        self._bankers_guard = guard
    
    def start(self) -> None:
        """Start the transaction engine with worker threads."""
        with self._lock:
            if self._running:
                raise RuntimeError("Engine is already running")
            self._running = True
        
        # Start worker threads
        for i in range(len(self._workers), self._num_workers):  # Default 3 workers
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TransactionWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
    
    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the transaction engine gracefully.
        
        Args:
            timeout (float): Seconds to wait for workers to finish
        """
        with self._lock:
            self._running = False
        
        # Signal workers by sending sentinel values
        for _ in self._workers:
            self._transaction_queue.put(None)
        
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=timeout)
        
        self._workers.clear()
    
    def submit_transaction(self, transaction: Transaction) -> str:
        """
        Submit a transaction to the engine.
        
        Args:
            transaction (Transaction): The transaction to process
            
        Returns:
            str: The assigned transaction ID
            
        Raises:
            RuntimeError: If engine is not running
        """
        if not self._running:
            raise RuntimeError("Engine is not running")
        
        with self._lock:
            self._transaction_counter += 1
            transaction.transaction_id = f"T{self._transaction_counter:06d}"
        
        # Assign fictitious block number for SCAN scheduling
        import random
        transaction.block_number = random.randint(0, 100)
        
        self._transaction_queue.put(transaction)
        return transaction.transaction_id
    
    def _worker_loop(self) -> None:
        """Main worker thread loop (consumer)."""
        while True:
            try:
                # Wait for a transaction with timeout to allow graceful shutdown
                transaction = self._transaction_queue.get(timeout=1.0)
                
                # Sentinel value signals shutdown
                if transaction is None:
                    self._transaction_queue.task_done()
                    break
                
                # Mark as authorized
                transaction.mark_authorized()
                
                # Acquire semaphore slot before processing
                self._semaphore.acquire()
                try:
                    # Mark as processing
                    transaction.mark_processing()
                    result = self._process_transaction(transaction)
                    self._result_queue.put(result)
                finally:
                    self._semaphore.release()
                
                self._transaction_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.exception(f"Worker error: {e}")
    
    def _process_transaction(self, transaction: Transaction) -> Transaction:
        """
        Execute a transaction against the account(s).
        
        Applies authorization and deadlock prevention checks before execution.
        
        Args:
            transaction (Transaction): The transaction to execute
            
        Returns:
            Transaction: Updated transaction with status and result
        """
        try:
            # Apply RBAC authorization if hook is set
            if self._authorization_hook:
                if not self._authorization_hook(transaction):
                    transaction.mark_denied("Authorization failed")
                    return transaction
            
            # Validate accounts exist
            if transaction.source_account_id not in self._accounts:
                transaction.mark_failed("Source account not found")
                return transaction
            
            source_account = self._accounts[transaction.source_account_id]
            
            # Process transaction by type
            if transaction.transaction_type == TransactionType.DEPOSIT:
                if source_account.deposit(transaction.amount, 
                                         f"Deposit by {transaction.user_id}"):
                    transaction.mark_completed()
                else:
                    transaction.mark_failed("Deposit operation failed")
            
            elif transaction.transaction_type == TransactionType.WITHDRAWAL:
                if source_account.withdraw(transaction.amount,
                                          f"Withdrawal by {transaction.user_id}"):
                    transaction.mark_completed()
                else:
                    transaction.mark_failed("Withdrawal operation failed")
            
            elif transaction.transaction_type == TransactionType.TRANSFER:
                if not transaction.destination_account_id:
                    transaction.mark_failed("Destination account not specified")
                    return transaction
                
                if transaction.destination_account_id not in self._accounts:
                    transaction.mark_failed("Destination account not found")
                    return transaction
                
                dest_account = self._accounts[transaction.destination_account_id]
                
                # Apply Banker's Algorithm if guard is set
                if self._bankers_guard:
                    if not self._bankers_guard(transaction):
                        transaction.mark_denied("Banker's Algorithm check failed")
                        return transaction
                
                # Execute transfer with ordered locking to prevent deadlock
                if self._execute_transfer(source_account, dest_account, 
                                        transaction.amount,
                                        transaction.source_account_id,
                                        transaction.destination_account_id):
                    transaction.mark_completed()
                else:
                    transaction.mark_failed("Transfer operation failed")
            
            elif transaction.transaction_type == TransactionType.QUERY:
                # Query operations don't modify state, always succeed
                transaction.metadata['balance'] = source_account.get_balance()
                transaction.mark_completed()
            
            else:
                transaction.mark_failed("Unknown transaction type")
            
            return transaction
            
        except ValueError as e:
            transaction.mark_failed(f"Validation error: {str(e)}")
            return transaction
        except Exception as e:
            logging.exception(f"Transaction {transaction.transaction_id} error: {e}")
            transaction.mark_failed(f"Exception: {str(e)}")
            return transaction
    
    def _execute_transfer(self, source_account: 'Account', 
                         dest_account: 'Account',
                         amount: float,
                         source_id: str,
                         dest_id: str) -> bool:
        """
        Execute a transfer between two accounts with ordered locking.
        
        Manages synchronization orchestration for transfer operations.
        Acquires locks in account ID order to prevent circular wait deadlock.
        Performs: verify balance -> debit source -> credit destination
        
        Args:
            source_account (Account): Source account object
            dest_account (Account): Destination account object
            amount (float): Amount to transfer
            source_id (str): Source account ID
            dest_id (str): Destination account ID
            
        Returns:
            bool: True if transfer succeeded, False otherwise
        """
        # Order locks by account ID to prevent deadlock
        if source_id < dest_id:
            first_account, second_account = source_account, dest_account
        else:
            first_account, second_account = dest_account, source_account
        
        # Acquire locks in order
        first_account.acquire_lock()
        try:
            second_account.acquire_lock()
            try:
                # Verify balance
                if source_account.get_balance() < amount:
                    return False
                
                # Debit source account
                source_account.transfer_internal(amount, is_debit=True)
                
                # Credit destination account
                dest_account.transfer_internal(amount, is_debit=False)
                
                return True
            finally:
                second_account.release_lock()
        finally:
            first_account.release_lock()
    
    def get_pending_count(self) -> int:
        """Get count of pending transactions in queue."""
        return self._transaction_queue.qsize()
    
    def get_result(self, timeout: float = 1.0) -> Optional[Transaction]:
        """
        Retrieve a completed transaction from results queue.
        
        Args:
            timeout (float): Seconds to wait for a result
            
        Returns:
            Transaction or None if timeout
        """
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_all_results(self) -> list:
        """
        Retrieve all completed transactions from results queue.
        
        Returns:
            list: All available completed transactions
        """
        results = []
        while True:
            try:
                result = self._result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results
    
    def wait_completion(self):
        """
        Wait for all pending transactions to complete.
                   
        Returns:
            bool: True if all completed, False if timeout
        """
        self._transaction_queue.join()
        return True