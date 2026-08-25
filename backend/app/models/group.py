from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, Date, Integer, ForeignKey, Index, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category


class Group(Base, TimestampMixin):
    """
    Groups that bundle users together for Splitwise-style expense sharing.
    """
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    members: Mapped[List["GroupMember"]] = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["GroupExpense"]] = relationship(
        "GroupExpense", back_populates="group", cascade="all, delete-orphan"
    )
    settlements: Mapped[List["GroupSettlement"]] = relationship(
        "GroupSettlement", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base, TimestampMixin):
    """
    Association table mapping users to groups with custom roles.
    """
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)  # "admin", "member"

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="members")
    user: Mapped["User"] = relationship("User")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""

    @property
    def joined_at(self) -> datetime:
        return self.created_at

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member_user"),
    )


class GroupExpense(Base, TimestampMixin):
    """
    An expense logged within a shared group. Supports multiple payers and custom splits.
    """
    __tablename__ = "group_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    split_method: Mapped[str] = mapped_column(String(50), nullable=False)  # "equal", "exact", "percentage", "shares"

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="expenses")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    category: Mapped["Category"] = relationship("Category")
    payments: Mapped[List["GroupExpensePayment"]] = relationship(
        "GroupExpensePayment", back_populates="expense", cascade="all, delete-orphan"
    )
    participants: Mapped[List["GroupExpenseParticipant"]] = relationship(
        "GroupExpenseParticipant", back_populates="expense", cascade="all, delete-orphan"
    )


class GroupExpensePayment(Base):
    """
    Tracks which group members paid how much towards a group expense.
    Supports single or multiple payers.
    """
    __tablename__ = "group_expense_payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    group_expense_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    expense: Mapped["GroupExpense"] = relationship("GroupExpense", back_populates="payments")
    user: Mapped["User"] = relationship("User")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""

    __table_args__ = (
        UniqueConstraint("group_expense_id", "user_id", name="uq_group_expense_payment_user"),
    )


class GroupExpenseParticipant(Base):
    """
    Tracks the share value and final calculated debt owed by each participant for a group expense.
    """
    __tablename__ = "group_expense_participants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    group_expense_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    share_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # User input target split value
    calculated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # Absolute calculated owe amount

    # Relationships
    expense: Mapped["GroupExpense"] = relationship("GroupExpense", back_populates="participants")
    user: Mapped["User"] = relationship("User")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""

    __table_args__ = (
        UniqueConstraint("group_expense_id", "user_id", name="uq_group_expense_participant_user"),
    )


class GroupSettlement(Base, TimestampMixin):
    """
    Tracks peer-to-peer settlement payments between members to resolve group balances.
    """
    __tablename__ = "group_settlements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receiver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="settlements")
    payer: Mapped["User"] = relationship("User", foreign_keys=[payer_id])
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_id])
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

    @property
    def payer_name(self) -> str:
        return self.payer.full_name if self.payer else ""

    @property
    def payer_email(self) -> str:
        return self.payer.email if self.payer else ""

    @property
    def receiver_name(self) -> str:
        return self.receiver.full_name if self.receiver else ""

    @property
    def receiver_email(self) -> str:
        return self.receiver.email if self.receiver else ""
