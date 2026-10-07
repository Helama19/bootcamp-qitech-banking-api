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
from models.account_status import AccountStatus
from models.client import Client


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)

    account_key = Column(
        UUID(as_uuid=False),
        nullable=False,
    )

    client_id = Column(
        Integer,
        ForeignKey(Client.id),
        nullable=False,
    )

    status_id = Column(
        Integer,
        ForeignKey(AccountStatus.id),
        nullable=False,
    )

    balance = Column(
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
        UniqueConstraint("account_key"),
        UniqueConstraint("client_id"),
        CheckConstraint("balance >= 0"),
    )

    client = relationship(
        "Client",
        foreign_keys=[client_id],
        lazy="selectin",
    )

    status = relationship(
        "AccountStatus",
        foreign_keys=[status_id],
        lazy="selectin",
    )