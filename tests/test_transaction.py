import pytest
import threading
import time
import random
from datetime import datetime
from typing import Dict
from unittest.mock import Mock, patch, MagicMock

# Import modules under test
import sys
sys.path.insert(0, '/home/victo/Uni/Sistemas Operativos/banco-transacciones-so')

from core.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionBuilder
)
from core.account import Account
from core.transaction_engine import TransactionEngine


# ==================== UNIT TESTS ====================

class TestTransactionType:
    """Unit tests for TransactionType enum."""
    
    def test_transaction_types_exist(self):
        """Verify all transaction types are defined."""
        assert TransactionType.DEPOSIT
        assert TransactionType.WITHDRAWAL
        assert TransactionType.TRANSFER
        assert TransactionType.QUERY
    
    def test_transaction_type_values(self):
        """Test transaction type string values."""
        assert TransactionType.DEPOSIT.value == "DEPOSIT"
        assert TransactionType.WITHDRAWAL.value == "WITHDRAWAL"
        assert TransactionType.TRANSFER.value == "TRANSFER"
        assert TransactionType.QUERY.value == "QUERY"


class TestTransactionStatus:
    """Unit tests for TransactionStatus enum."""
    
    def test_transaction_statuses_exist(self):
        """Verify all transaction statuses are defined."""
        assert TransactionStatus.PENDING
        assert TransactionStatus.AUTHORIZED
        assert TransactionStatus.PROCESSING
        assert TransactionStatus.COMPLETED
        assert TransactionStatus.FAILED
        assert TransactionStatus.DENIED
    
    def test_transaction_status_values(self):
        """Test transaction status string values."""
        assert TransactionStatus.PENDING.value == "PENDING"
        assert TransactionStatus.COMPLETED.value == "COMPLETED"
        assert TransactionStatus.FAILED.value == "FAILED"


class TestTransaction:
    """Unit tests for Transaction dataclass."""
    
    @pytest.fixture
    def valid_transaction(self):
        """Create a valid deposit transaction."""
        return Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
    
    def test_transaction_creation(self, valid_transaction):
        """Test basic transaction creation."""
        assert valid_transaction.transaction_type == TransactionType.DEPOSIT
        assert valid_transaction.source_account_id == "ACC001"
        assert valid_transaction.amount == 100.0
        assert valid_transaction.status == TransactionStatus.PENDING
    
    def test_transaction_timestamp_auto_set(self):
        """Test that timestamp is auto-set if not provided."""
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=50.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert txn.timestamp is not None
        assert isinstance(txn.timestamp, datetime)
    
    def test_transaction_validation_negative_amount(self):
        """Test validation rejects negative amounts."""
        with pytest.raises(ValueError, match="must be positive"):
            Transaction(
                transaction_type=TransactionType.DEPOSIT,
                source_account_id="ACC001",
                amount=-100.0,
                user_id="user1",
                user_role="CUSTOMER"
            )
    
    def test_transaction_validation_zero_amount(self):
        """Test validation rejects zero amounts."""
        with pytest.raises(ValueError, match="must be positive"):
            Transaction(
                transaction_type=TransactionType.DEPOSIT,
                source_account_id="ACC001",
                amount=0.0,
                user_id="user1",
                user_role="CUSTOMER"
            )
    
    def test_transaction_query_accepts_zero_amount(self):
        """Test that query transactions accept zero amount."""
        txn = Transaction(
            transaction_type=TransactionType.QUERY,
            source_account_id="ACC001",
            amount=0.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert txn.amount == 0.0
    
    def test_transaction_transfer_requires_destination(self):
        """Test validation requires destination for transfers."""
        with pytest.raises(ValueError, match="destination_account_id"):
            Transaction(
                transaction_type=TransactionType.TRANSFER,
                source_account_id="ACC001",
                destination_account_id=None,
                amount=100.0,
                user_id="user1",
                user_role="CUSTOMER"
            )
    
    def test_transaction_transfer_same_source_dest(self):
        """Test validation rejects same source and destination."""
        with pytest.raises(ValueError, match="cannot be the same"):
            Transaction(
                transaction_type=TransactionType.TRANSFER,
                source_account_id="ACC001",
                destination_account_id="ACC001",
                amount=100.0,
                user_id="user1",
                user_role="CUSTOMER"
            )
    
    def test_mark_authorized(self, valid_transaction):
        """Test marking transaction as authorized."""
        valid_transaction.mark_authorized()
        assert valid_transaction.status == TransactionStatus.AUTHORIZED
        assert 'authorized_at' in valid_transaction.metadata
    
    def test_mark_processing(self, valid_transaction):
        """Test marking transaction as processing."""
        valid_transaction.mark_processing()
        assert valid_transaction.status == TransactionStatus.PROCESSING
        assert 'processing_started_at' in valid_transaction.metadata
    
    def test_mark_completed(self, valid_transaction):
        """Test marking transaction as completed."""
        valid_transaction.mark_completed()
        assert valid_transaction.status == TransactionStatus.COMPLETED
        assert 'completed_at' in valid_transaction.metadata
    
    def test_mark_failed(self, valid_transaction):
        """Test marking transaction as failed."""
        valid_transaction.mark_failed("Insufficient funds")
        assert valid_transaction.status == TransactionStatus.FAILED
        assert valid_transaction.metadata['failure_reason'] == "Insufficient funds"
    
    def test_mark_denied(self, valid_transaction):
        """Test marking transaction as denied."""
        valid_transaction.mark_denied("Access denied")
        assert valid_transaction.status == TransactionStatus.DENIED
        assert valid_transaction.metadata['denial_reason'] == "Access denied"
    
    def test_get_operation_summary_deposit(self):
        """Test operation summary for deposit."""
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        summary = txn.get_operation_summary()
        assert "Deposit" in summary
        assert "100.00" in summary
    
    def test_get_operation_summary_transfer(self):
        """Test operation summary for transfer."""
        txn = Transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account_id="ACC001",
            destination_account_id="ACC002",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        summary = txn.get_operation_summary()
        assert "Transfer" in summary
        assert "ACC001" in summary
        assert "ACC002" in summary
    
    def test_get_affected_accounts_single(self):
        """Test getting affected accounts for single-account transaction."""
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        accounts = txn.get_affected_accounts()
        assert accounts == ["ACC001"]
    
    def test_get_affected_accounts_multi(self):
        """Test getting affected accounts for multi-account transaction."""
        txn = Transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account_id="ACC001",
            destination_account_id="ACC002",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        accounts = txn.get_affected_accounts()
        assert len(accounts) == 2
        assert "ACC001" in accounts
        assert "ACC002" in accounts
    
    def test_is_multi_account(self):
        """Test multi-account transaction detection."""
        txn_single = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert not txn_single.is_multi_account()
        
        txn_multi = Transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account_id="ACC001",
            destination_account_id="ACC002",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert txn_multi.is_multi_account()
    
    def test_requires_authorization(self):
        """Test authorization requirement detection."""
        txn_query = Transaction(
            transaction_type=TransactionType.QUERY,
            source_account_id="ACC001",
            amount=0.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert not txn_query.requires_authorization()
        
        txn_deposit = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        assert txn_deposit.requires_authorization()
    
    def test_transaction_to_dict(self, valid_transaction):
        """Test transaction serialization to dict."""
        data = valid_transaction.to_dict()
        assert data['transaction_type'] == "DEPOSIT"
        assert data['amount'] == 100.0
        assert isinstance(data['timestamp'], str)
    
    def test_transaction_from_dict(self):
        """Test transaction deserialization from dict."""
        data = {
            'transaction_id': 'T000001',
            'transaction_type': 'DEPOSIT',
            'source_account_id': 'ACC001',
            'destination_account_id': None,
            'amount': 100.0,
            'user_id': 'user1',
            'user_role': 'CUSTOMER',
            'timestamp': datetime.now().isoformat(),
            'block_number': 0,
            'status': 'PENDING',
            'description': 'Test deposit',
            'metadata': {}
        }
        txn = Transaction.from_dict(data)
        assert txn.transaction_id == "T000001"
        assert txn.transaction_type == TransactionType.DEPOSIT
        assert isinstance(txn.timestamp, datetime)


# ==================== BUILDER TESTS ====================

class TestTransactionBuilder:
    """Unit tests for TransactionBuilder.
    
    The builder does NOT accept a transaction_id — the engine is solely
    responsible for assigning IDs at submission time.
    """
    
    def test_builder_deposit(self):
        """Test building a deposit transaction."""
        # Option A: builder only takes user_id and user_role
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = builder.with_deposit("ACC001", 100.0).build()
        
        assert txn.transaction_type == TransactionType.DEPOSIT
        assert txn.source_account_id == "ACC001"
        assert txn.amount == 100.0
        assert txn.user_id == "user1"
        assert txn.user_role == "CUSTOMER"
    
    def test_builder_withdrawal(self):
        """Test building a withdrawal transaction."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = builder.with_withdrawal("ACC001", 50.0).build()
        
        assert txn.transaction_type == TransactionType.WITHDRAWAL
        assert txn.source_account_id == "ACC001"
        assert txn.amount == 50.0
    
    def test_builder_transfer(self):
        """Test building a transfer transaction."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = builder.with_transfer("ACC001", "ACC002", 75.0).build()
        
        assert txn.transaction_type == TransactionType.TRANSFER
        assert txn.source_account_id == "ACC001"
        assert txn.destination_account_id == "ACC002"
        assert txn.amount == 75.0
    
    def test_builder_query(self):
        """Test building a query transaction."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = builder.with_query("ACC001").build()
        
        assert txn.transaction_type == TransactionType.QUERY
        assert txn.source_account_id == "ACC001"
    
    def test_builder_with_metadata(self):
        """Test adding metadata to transaction."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = (builder.with_deposit("ACC001", 100.0)
                      .with_metadata("source", "mobile_app")
                      .build())
        
        assert txn.metadata['source'] == "mobile_app"
    
    def test_builder_with_block_number(self):
        """Test setting a block number for SCAN scheduling."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = (builder.with_deposit("ACC001", 100.0)
                      .with_block_number(42)
                      .build())
        
        assert txn.block_number == 42
    
    def test_builder_missing_type(self):
        """Test builder raises if no transaction type was set."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        with pytest.raises(ValueError, match="Transaction type must be set"):
            builder.build()
    
    def test_builder_missing_amount(self):
        """Test builder raises if amount is missing for non-query transactions."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        builder._transaction_type = TransactionType.DEPOSIT
        builder._source_account_id = "ACC001"
        with pytest.raises(ValueError, match="Amount must be set"):
            builder.build()
    
    def test_builder_id_is_none_before_engine(self):
        """Test that transaction_id is None before submission to the engine."""
        builder = TransactionBuilder("user1", "CUSTOMER")
        txn = builder.with_deposit("ACC001", 200.0).build()
        # Engine hasn't assigned an ID yet
        assert txn.transaction_id is None
    
    def test_engine_assigns_id_on_submit(self):
        """Test that the engine (not the builder) assigns the transaction ID."""
        accounts = {"ACC001": Account("ACC001", "Alice", 1000.0)}
        engine = TransactionEngine(accounts, max_concurrent=2, num_workers=1)
        engine.start()
        try:
            txn = TransactionBuilder("user1", "CUSTOMER").with_deposit("ACC001", 50.0).build()
            assert txn.transaction_id is None  # not yet assigned
            
            txn_id = engine.submit_transaction(txn)
            assert txn_id.startswith("T")
            assert txn.transaction_id == txn_id  # engine assigned it
        finally:
            engine.stop()


# ==================== ACCOUNT UNIT TESTS ====================

class TestAccount:
    """Unit tests for Account."""
    
    @pytest.fixture
    def account(self):
        """Create a test account."""
        return Account("ACC001", "John Doe", 1000.0)
    
    def test_account_creation(self, account):
        """Test account initialization."""
        assert account.account_id == "ACC001"
        assert account.holder_name == "John Doe"
        assert account.balance == 1000.0
        assert account._lock is not None
    
    def test_account_deposit(self, account):
        """Test deposit operation."""
        result = account.deposit(100.0, "Test deposit")
        assert result is True
        assert account.balance == 1100.0
    
    def test_account_deposit_negative(self, account):
        """Test deposit rejects negative amount."""
        with pytest.raises(ValueError, match="must be positive"):
            account.deposit(-50.0)
    
    def test_account_withdrawal(self, account):
        """Test withdrawal operation."""
        result = account.withdraw(100.0, "Test withdrawal")
        assert result is True
        assert account.balance == 900.0
    
    def test_account_withdrawal_insufficient_funds(self, account):
        """Test withdrawal fails with insufficient funds."""
        result = account.withdraw(2000.0)
        assert result is False
        assert account.balance == 1000.0
    
    def test_account_get_balance(self, account):
        """Test getting balance."""
        balance = account.get_balance()
        assert balance == 1000.0
    
    def test_account_can_transfer(self, account):
        """Test transfer capability check."""
        assert account.can_transfer(500.0) is True
        assert account.can_transfer(2000.0) is False
        assert account.can_transfer(0.0) is False
    
    def test_account_transaction_history(self, account):
        """Test transaction history recording."""
        account.deposit(100.0)
        account.withdraw(50.0)
        
        history = account.get_transaction_history()
        assert len(history) >= 2
        assert history[0]['type'] == 'DEPOSIT'
        assert history[1]['type'] == 'WITHDRAWAL'
    
    def test_account_lock_operations(self, account):
        """Test lock acquisition and release."""
        account.acquire_lock()
        assert account._lock.locked() is True
        account.release_lock()
        assert account._lock.locked() is False


# ==================== CONCURRENCY TESTS ====================

class TestAccountConcurrency:
    """Concurrency tests for Account operations."""
    
    def test_concurrent_deposits(self):
        """Test concurrent deposit operations maintain consistency."""
        account = Account("ACC001", "Test", 0.0)
        num_threads = 10
        deposits_per_thread = 100
        amount = 1.0
        
        def deposit_thread():
            for _ in range(deposits_per_thread):
                account.deposit(amount)
        
        threads = [threading.Thread(target=deposit_thread) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        expected_balance = num_threads * deposits_per_thread * amount
        assert account.balance == expected_balance
    
    def test_concurrent_withdrawals(self):
        """Test concurrent withdrawal operations maintain consistency."""
        account = Account("ACC001", "Test", 10000.0)
        num_threads = 10
        withdrawal_amount = 50.0
        
        successful_withdrawals = []
        lock = threading.Lock()
        
        def withdraw_thread():
            for _ in range(10):
                result = account.withdraw(withdrawal_amount)
                if result:
                    with lock:
                        successful_withdrawals.append(result)
        
        threads = [threading.Thread(target=withdraw_thread) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert account.balance >= 0
        assert account.balance + (len(successful_withdrawals) * withdrawal_amount) <= 10000.0 + 1.0
    
    def test_concurrent_mixed_operations(self):
        """Test concurrent mixed operations maintain consistency."""
        account = Account("ACC001", "Test", 5000.0)
        operations = []
        lock = threading.Lock()
        
        def mixed_operations():
            for _ in range(50):
                op = random.choice(['deposit', 'withdraw'])
                amount = random.uniform(1.0, 100.0)
                
                if op == 'deposit':
                    account.deposit(amount)
                    with lock:
                        operations.append(('deposit', amount, True))
                else:
                    result = account.withdraw(amount)
                    with lock:
                        operations.append(('withdraw', amount, result))
        
        threads = [threading.Thread(target=mixed_operations) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        expected = 5000.0
        for op_type, amount, success in operations:
            if op_type == 'deposit':
                expected += amount
            elif success:
                expected -= amount
        
        assert abs(account.balance - expected) < 0.01


class TestTransactionEngineConcurrency:
    """Concurrency tests for TransactionEngine."""
    
    @pytest.fixture
    def engine_with_accounts(self):
        """Create engine with test accounts."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 1000.0),
            "ACC002": Account("ACC002", "Bob", 1000.0),
            "ACC003": Account("ACC003", "Charlie", 1000.0),
        }
        engine = TransactionEngine(accounts, max_concurrent=5, num_workers=3)
        engine.start()
        yield engine
        engine.stop()
    
    def test_concurrent_submissions(self, engine_with_accounts):
        """Test submitting multiple transactions concurrently."""
        engine = engine_with_accounts
        submitted = []
        lock = threading.Lock()
        
        def submit_transactions():
            for i in range(10):
                txn = Transaction(
                    transaction_type=TransactionType.DEPOSIT,
                    source_account_id="ACC001",
                    amount=10.0,
                    user_id="user1",
                    user_role="CUSTOMER"
                )
                txn_id = engine.submit_transaction(txn)
                with lock:
                    submitted.append(txn_id)
        
        threads = [threading.Thread(target=submit_transactions) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(submitted) == 50
        # All IDs must be unique — the engine counter must be thread-safe
        assert len(set(submitted)) == 50
        engine.wait_completion()
        results = engine.get_all_results()
        assert len(results) > 0
    
    def test_semaphore_limits_concurrency(self, engine_with_accounts):
        """Test that semaphore limits concurrent transactions."""
        engine = engine_with_accounts
        max_concurrent = engine._max_concurrent
        
        concurrent_count = []
        max_observed = [0]
        lock = threading.Lock()
        
        original_process = engine._process_transaction
        
        def tracked_process(txn):
            with lock:
                concurrent_count.append(1)
                max_observed[0] = max(max_observed[0], len(concurrent_count))
            
            time.sleep(0.01)
            result = original_process(txn)
            
            with lock:
                concurrent_count.pop()
            
            return result
        
        engine._process_transaction = tracked_process
        
        for i in range(20):
            txn = Transaction(
                transaction_type=TransactionType.QUERY,
                source_account_id="ACC001",
                amount=0.0,
                user_id="user1",
                user_role="CUSTOMER"
            )
            engine.submit_transaction(txn)
        
        engine.wait_completion()
        assert max_observed[0] <= max_concurrent + 1


# ==================== INTEGRATION TESTS ====================

class TestTransactionEngineIntegration:
    """Integration tests for TransactionEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create and start transaction engine."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 5000.0),
            "ACC002": Account("ACC002", "Bob", 5000.0),
            "ACC003": Account("ACC003", "Charlie", 5000.0),
        }
        engine = TransactionEngine(accounts, max_concurrent=5, num_workers=3)
        engine.start()
        yield engine
        engine.stop()
    
    def test_deposit_transaction_flow(self, engine):
        """Test complete deposit transaction flow."""
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=500.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        txn_id = engine.submit_transaction(txn)
        assert txn_id.startswith("T")
        
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result is not None
        assert result.status == TransactionStatus.COMPLETED
        assert engine._accounts["ACC001"].balance == 5500.0
    
    def test_withdrawal_transaction_flow(self, engine):
        """Test complete withdrawal transaction flow."""
        txn = Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            source_account_id="ACC001",
            amount=1000.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.COMPLETED
        assert engine._accounts["ACC001"].balance == 4000.0
    
    def test_transfer_transaction_flow(self, engine):
        """Test complete transfer transaction flow."""
        txn = Transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account_id="ACC001",
            destination_account_id="ACC002",
            amount=1000.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.COMPLETED
        assert engine._accounts["ACC001"].balance == 4000.0
        assert engine._accounts["ACC002"].balance == 6000.0
    
    def test_query_transaction_flow(self, engine):
        """Test complete query transaction flow."""
        txn = Transaction(
            transaction_type=TransactionType.QUERY,
            source_account_id="ACC001",
            amount=0.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.COMPLETED
        assert result.metadata['balance'] == 5000.0
    
    def test_insufficient_funds_withdrawal(self, engine):
        """Test withdrawal fails with insufficient funds."""
        txn = Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            source_account_id="ACC001",
            amount=10000.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.FAILED
        assert engine._accounts["ACC001"].balance == 5000.0
    
    def test_multiple_transactions_sequence(self, engine):
        """Test sequence of multiple transactions with keyword arguments."""
        # Using keyword args because the original dataclass field order is:
        # source_account_id, amount, user_id, user_role, transaction_type, ...
        transactions = [
            Transaction(
                transaction_type=TransactionType.DEPOSIT,
                source_account_id="ACC001",
                amount=500.0,
                user_id="user1",
                user_role="CUSTOMER"
            ),
            Transaction(
                transaction_type=TransactionType.WITHDRAWAL,
                source_account_id="ACC001",
                amount=200.0,
                user_id="user1",
                user_role="CUSTOMER"
            ),
            Transaction(
                transaction_type=TransactionType.TRANSFER,
                source_account_id="ACC001",
                destination_account_id="ACC002",
                amount=300.0,
                user_id="user1",
                user_role="CUSTOMER"
            ),
        ]
        
        for txn in transactions:
            engine.submit_transaction(txn)
        
        engine.wait_completion()
        results = engine.get_all_results()
        
        assert len(results) >= 3
        assert all(r.status == TransactionStatus.COMPLETED for r in results)
        
        # ACC001: 5000 + 500 - 200 - 300 = 5000
        # ACC002: 5000 + 300 = 5300
        assert engine._accounts["ACC001"].balance == 5000.0
        assert engine._accounts["ACC002"].balance == 5300.0
    
    def test_authorization_hook(self, engine):
        """Test transaction authorization hook."""
        def auth_hook(txn):
            return txn.user_id != "restricted_user"
        
        engine.set_authorization_hook(auth_hook)
        
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="ACC001",
            amount=100.0,
            user_id="restricted_user",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.DENIED
    
    def test_nonexistent_source_account(self, engine):
        """Test transaction fails gracefully for unknown source account."""
        txn = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            source_account_id="GHOST999",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.FAILED
    
    def test_nonexistent_destination_account(self, engine):
        """Test transfer fails gracefully for unknown destination account."""
        txn = Transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account_id="ACC001",
            destination_account_id="GHOST999",
            amount=100.0,
            user_id="user1",
            user_role="CUSTOMER"
        )
        
        engine.submit_transaction(txn)
        engine.wait_completion()
        result = engine.get_result(timeout=2.0)
        
        assert result.status == TransactionStatus.FAILED
        # Source balance must be untouched
        assert engine._accounts["ACC001"].balance == 5000.0


# ==================== STRESS TESTS ====================

class TestStress:
    """Stress tests for the transaction system."""
    
    def test_high_volume_transactions(self):
        """Stress test with high volume of transactions."""
        accounts = {
            f"ACC{i:03d}": Account(f"ACC{i:03d}", f"User{i}", 10000.0)
            for i in range(10)
        }
        
        engine = TransactionEngine(accounts, max_concurrent=10, num_workers=5)
        engine.start()
        
        try:
            num_transactions = 500
            for i in range(num_transactions):
                source = f"ACC{i % 10:03d}"
                txn = Transaction(
                    transaction_type=TransactionType.DEPOSIT,
                    source_account_id=source,
                    amount=random.uniform(1.0, 100.0),
                    user_id=f"user{i % 5}",
                    user_role="CUSTOMER"
                )
                engine.submit_transaction(txn)
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) >= num_transactions * 0.95
            
        finally:
            engine.stop()
    
    def test_large_transaction_amounts(self):
        """Stress test with large transaction amounts."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 1_000_000.0),
            "ACC002": Account("ACC002", "Bob", 1_000_000.0),
        }
        
        engine = TransactionEngine(accounts, max_concurrent=5, num_workers=3)
        engine.start()
        
        try:
            for i in range(100):
                txn = Transaction(
                    transaction_type=TransactionType.DEPOSIT,
                    source_account_id="ACC001",
                    amount=50000.0,
                    user_id="user1",
                    user_role="CUSTOMER"
                )
                engine.submit_transaction(txn)
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) >= 95
            assert accounts["ACC001"].balance > 1_000_000.0
            
        finally:
            engine.stop()
    
    def test_many_workers_many_transactions(self):
        """Stress test with many workers and transactions."""
        accounts = {
            f"ACC{i:03d}": Account(f"ACC{i:03d}", f"User{i}", 5000.0)
            for i in range(20)
        }
        
        engine = TransactionEngine(accounts, max_concurrent=20, num_workers=10)
        engine.start()
        
        try:
            for i in range(1000):
                source = f"ACC{i % 20:03d}"
                dest = f"ACC{(i + 1) % 20:03d}"
                txn = Transaction(
                    transaction_type=TransactionType.TRANSFER if i % 2 == 0 else TransactionType.DEPOSIT,
                    source_account_id=source,
                    destination_account_id=dest if i % 2 == 0 else None,
                    amount=random.uniform(10.0, 100.0),
                    user_id=f"user{i % 5}",
                    user_role="CUSTOMER"
                )
                engine.submit_transaction(txn)
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) >= 900
            
        finally:
            engine.stop()


# ==================== RACE CONDITION TESTS ====================

class TestRaceConditions:
    """Tests for detecting and preventing race conditions."""
    
    def test_concurrent_transfer_same_accounts(self):
        """Test race condition: concurrent transfers on same accounts."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 10000.0),
            "ACC002": Account("ACC002", "Bob", 10000.0),
        }
        
        engine = TransactionEngine(accounts, max_concurrent=10, num_workers=5)
        engine.start()
        
        try:
            for i in range(50):
                txn = Transaction(
                    transaction_type=TransactionType.TRANSFER,
                    source_account_id="ACC001" if i % 2 == 0 else "ACC002",
                    destination_account_id="ACC002" if i % 2 == 0 else "ACC001",
                    amount=10.0,
                    user_id="user1",
                    user_role="CUSTOMER"
                )
                engine.submit_transaction(txn)
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) >= 45
            
            # Total money must be conserved
            total = accounts["ACC001"].balance + accounts["ACC002"].balance
            assert abs(total - 20000.0) < 0.01
            
        finally:
            engine.stop()
    
    def test_circular_transfer_deadlock_prevention(self):
        """Test that ordered locking prevents circular deadlock."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 1000.0),
            "ACC002": Account("ACC002", "Bob", 1000.0),
            "ACC003": Account("ACC003", "Charlie", 1000.0),
        }
        
        engine = TransactionEngine(accounts, max_concurrent=10, num_workers=5)
        engine.start()
        
        try:
            transfers = [
                ("ACC001", "ACC002", 100.0),
                ("ACC002", "ACC003", 100.0),
                ("ACC003", "ACC001", 100.0),
            ]
            
            for _ in range(20):
                for source, dest, amount in transfers:
                    txn = Transaction(
                        transaction_type=TransactionType.TRANSFER,
                        source_account_id=source,
                        destination_account_id=dest,
                        amount=amount,
                        user_id="user1",
                        user_role="CUSTOMER"
                    )
                    engine.submit_transaction(txn)
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) > 0
            
            # Total money across the three accounts must be conserved
            total = sum(accounts[a].balance for a in ["ACC001", "ACC002", "ACC003"])
            assert abs(total - 3000.0) < 0.01
            
        finally:
            engine.stop()
    
    def test_balance_consistency_under_stress(self):
        """Test that account balances remain consistent under concurrent access."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 5000.0),
            "ACC002": Account("ACC002", "Bob", 5000.0),
        }
        
        engine = TransactionEngine(accounts, max_concurrent=10, num_workers=5)
        engine.start()
        
        try:
            for i in range(200):
                op_type = random.choice([
                    TransactionType.DEPOSIT,
                    TransactionType.WITHDRAWAL,
                    TransactionType.TRANSFER,
                    TransactionType.QUERY
                ])
                
                source = "ACC001" if i % 2 == 0 else "ACC002"
                dest = "ACC002" if i % 2 == 0 else "ACC001"
                amount = random.uniform(10.0, 500.0)
                
                txn = Transaction(
                    transaction_type=op_type,
                    source_account_id=source,
                    destination_account_id=dest if op_type == TransactionType.TRANSFER else None,
                    amount=amount if op_type != TransactionType.QUERY else 0.0,
                    user_id="user1",
                    user_role="CUSTOMER"
                )
                engine.submit_transaction(txn)
            
            engine.wait_completion()
            
            assert accounts["ACC001"].balance >= 0
            assert accounts["ACC002"].balance >= 0
            
            history1 = accounts["ACC001"].get_transaction_history()
            history2 = accounts["ACC002"].get_transaction_history()
            
            assert len(history1) > 0
            assert len(history2) > 0
            
        finally:
            engine.stop()
    
    def test_rapid_fire_transactions(self):
        """Test rapid-fire transaction submissions without race conditions."""
        accounts = {
            "ACC001": Account("ACC001", "Alice", 10000.0),
        }
        
        engine = TransactionEngine(accounts, max_concurrent=5, num_workers=3)
        engine.start()
        
        try:
            txn_ids = []
            for i in range(100):
                txn = Transaction(
                    transaction_type=TransactionType.DEPOSIT,
                    source_account_id="ACC001",
                    amount=1.0,
                    user_id="user1",
                    user_role="CUSTOMER"
                )
                txn_id = engine.submit_transaction(txn)
                txn_ids.append(txn_id)
            
            # All transaction IDs must be unique
            assert len(set(txn_ids)) == 100
            
            engine.wait_completion()
            results = engine.get_all_results()
            
            assert len(results) >= 95
            assert accounts["ACC001"].balance >= 10100.0
            
        finally:
            engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])