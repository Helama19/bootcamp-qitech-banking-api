from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.base import Base
from models.account import Account
from models.transaction_type import TransactionType


class FinancialTransaction(Base):
    __tablename__ = "financial_transaction"

    id = Column(Integer, primary_key=True)

    transaction_key = Column(
        UUID(as_uuid=False),
        nullable=False,
    )

    idempotency_key = Column(
        UUID(as_uuid=False),
        nullable=False,
    )

    transaction_type_id = Column(
        Integer,
        ForeignKey(TransactionType.id),
        nullable=False,
    )

    source_account_id = Column(
        Integer,
        ForeignKey(Account.id),
        nullable=True,
    )

    destination_account_id = Column(
        Integer,
        ForeignKey(Account.id),
        nullable=False,
    )

    amount = Column(
        Numeric(15, 2),
        nullable=False,
    )

    fee = Column(
        Numeric(15, 2),
        nullable=False,
        server_default="0.00",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("transaction_key"),
        UniqueConstraint("idempotency_key"),
        CheckConstraint("amount > 0"),
        CheckConstraint("fee >= 0"),
        CheckConstraint(
            "source_account_id IS NULL "
            "OR source_account_id <> destination_account_id"
        ),
    )

    transaction_type = relationship(
        "TransactionType",
        foreign_keys=[transaction_type_id],
        lazy="selectin",
    )

    source_account = relationship(
        "Account",
        foreign_keys=[source_account_id],
        lazy="selectin",
    )

    destination_account = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        lazy="selectin",
    )