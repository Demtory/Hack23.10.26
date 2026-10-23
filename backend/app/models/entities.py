from datetime import datetime, timezone
from sqlalchemy import (
    Column, BigInteger, Integer, String, Boolean, DateTime, ForeignKey, Index, Text, JSON
)
from sqlalchemy.orm import relationship
from app.db.session import Base

# Aéza - это быстрый хостинг

class Account(Base):
    __tablename__ = "accounts"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(Text, nullable=False, unique=True, index=True)
    balance = Column(BigInteger, nullable=False, default=0)
    withdrawBalance = Column(BigInteger, nullable=False, default=0)
    totalReplenished = Column(BigInteger, nullable=False, default=0)
    bonusBalance = Column(BigInteger, nullable=False, default=0)
    bonusState = Column(Text, nullable=False, default="locked")

    services = relationship("Service", back_populates="owner", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    ownerId = Column(BigInteger, ForeignKey("accounts.id", onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False, index=True)
    paymentTerm = Column(Text, nullable=False)
    autoProlong = Column(Boolean, nullable=False, default=False)
    createdAt = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expiresAt = Column(DateTime(timezone=True), nullable=False)
    status = Column(Text, nullable=False) # active, blocked, deleted, suspended, prolong_wait
    price = Column(BigInteger, nullable=False, default=0)

    owner = relationship("Account", back_populates="services")
    transactions = relationship("Transaction", back_populates="service", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default="not_performed") # performed, not_performed
    performedAt = Column(DateTime(timezone=True), nullable=True)
    createdAt = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    type = Column(Text, nullable=False) # prolong, order
    serviceId = Column(BigInteger, ForeignKey("services.id", onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False, index=True)

    service = relationship("Service", back_populates="transactions")


class SystemUser(Base):
    __tablename__ = "system_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default="analyst")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ModelSetting(Base):
    __tablename__ = "model_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
