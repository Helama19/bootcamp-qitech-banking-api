from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)

    client_key = Column(UUID(as_uuid=False), nullable=False)

    name = Column(String(255), nullable=False)
    document_number = Column(String(11), nullable=False)
    birth_date = Column(Date, nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("document_number"),
    )