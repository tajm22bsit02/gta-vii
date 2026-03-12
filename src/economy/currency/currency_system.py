"""Currency System - in-game monetary transactions."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional
import time


class TransactionType(Enum):
    """Categories of financial transaction."""

    MISSION_REWARD = auto()
    STORE_PURCHASE = auto()
    VEHICLE_PURCHASE = auto()
    PROPERTY_PURCHASE = auto()
    PROPERTY_INCOME = auto()
    FINE = auto()
    THEFT = auto()
    INVESTMENT = auto()
    MISC = auto()


@dataclass
class Transaction:
    """A single financial transaction record."""

    transaction_id: str
    transaction_type: TransactionType
    amount: int              # positive = income, negative = expense
    description: str
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    @property
    def is_income(self) -> bool:
        return self.amount > 0

    @property
    def is_expense(self) -> bool:
        return self.amount < 0


BalanceChangeCallback = Callable[[int, int, Transaction], None]  # (old, new, tx)


class CurrencySystem:
    """Manages the player's in-game finances.

    Tracks balance, maintains a full transaction ledger, and fires
    callbacks on balance change.
    """

    def __init__(self, initial_balance: int = 500) -> None:
        self._balance: int = initial_balance
        self._transactions: List[Transaction] = []
        self._balance_callbacks: List[BalanceChangeCallback] = []
        self._tx_counter: int = 0

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def total_earned(self) -> int:
        return sum(tx.amount for tx in self._transactions if tx.amount > 0)

    @property
    def total_spent(self) -> int:
        return abs(sum(tx.amount for tx in self._transactions if tx.amount < 0))

    # ------------------------------------------------------------------ #
    # Core operations                                                      #
    # ------------------------------------------------------------------ #

    def earn(
        self,
        amount: int,
        transaction_type: TransactionType = TransactionType.MISC,
        description: str = "",
    ) -> Transaction:
        """Add funds to the player's balance.

        Args:
            amount: Positive integer amount to add.
            transaction_type: Category of income.
            description: Human-readable description.

        Returns:
            The transaction record.
        """
        if amount <= 0:
            raise ValueError(f"Earn amount must be positive, got {amount}")
        return self._record(amount, transaction_type, description)

    def spend(
        self,
        amount: int,
        transaction_type: TransactionType = TransactionType.MISC,
        description: str = "",
    ) -> bool:
        """Deduct funds if balance is sufficient.

        Args:
            amount: Positive integer cost.
            transaction_type: Category of expense.
            description: Human-readable description.

        Returns:
            True if the transaction succeeded, False if insufficient funds.
        """
        if amount <= 0:
            raise ValueError(f"Spend amount must be positive, got {amount}")
        if self._balance < amount:
            return False
        self._record(-amount, transaction_type, description)
        return True

    def can_afford(self, amount: int) -> bool:
        return self._balance >= amount

    def add_change_callback(self, callback: BalanceChangeCallback) -> None:
        self._balance_callbacks.append(callback)

    def get_transaction_history(
        self, limit: int = 50
    ) -> List[Transaction]:
        """Return the most recent transactions."""
        return self._transactions[-limit:]

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _record(
        self,
        amount: int,
        transaction_type: TransactionType,
        description: str,
    ) -> Transaction:
        old_balance = self._balance
        self._balance += amount
        self._tx_counter += 1
        tx = Transaction(
            transaction_id=f"tx_{self._tx_counter:06d}",
            transaction_type=transaction_type,
            amount=amount,
            description=description,
        )
        self._transactions.append(tx)
        for cb in self._balance_callbacks:
            cb(old_balance, self._balance, tx)
        return tx

    def __repr__(self) -> str:
        return (
            f"CurrencySystem(balance=${self._balance:,}, "
            f"transactions={len(self._transactions)})"
        )
