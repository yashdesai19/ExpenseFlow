from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.models.group import Group, GroupExpense, GroupSettlement
from app.schemas.balance import GroupBalanceResponse, MemberBalanceSummary, SimplifiedDebt
from app.repositories.group_repo import group_repo


class BalanceService:
    """Service layer that aggregates transactions and simplifies debts."""

    @staticmethod
    def get_group_balances(db: Session, group_id: int, user: User) -> GroupBalanceResponse:
        # 1. Verify membership and retrieve group details
        group = group_repo.get_by_id(db, group_id=group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID {group_id} not found.",
            )

        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this group's balances.",
            )

        # Map member profiles for easy lookup
        members_map = {m.user_id: m.user for m in group.members if m.user}

        # Initialize tracking structure
        balances_tracker = {
            uid: {"paid": Decimal("0.00"), "owed": Decimal("0.00")}
            for uid in members_map.keys()
        }

        total_expenses = Decimal("0.00")

        # 2. Aggregate all expenses
        expenses = (
            db.query(GroupExpense)
            .options(
                joinedload(GroupExpense.payments),
                joinedload(GroupExpense.participants),
            )
            .filter(GroupExpense.group_id == group_id)
            .all()
        )

        for exp in expenses:
            total_expenses += exp.amount
            # Add paid amounts
            for p in exp.payments:
                if p.user_id in balances_tracker:
                    balances_tracker[p.user_id]["paid"] += p.amount
            # Add owed (spent) amounts
            for part in exp.participants:
                if part.user_id in balances_tracker:
                    balances_tracker[part.user_id]["owed"] += part.calculated_amount

        # 3. Aggregate all settlements
        settlements = (
            db.query(GroupSettlement)
            .filter(GroupSettlement.group_id == group_id)
            .all()
        )

        for sett in settlements:
            if sett.payer_id in balances_tracker:
                balances_tracker[sett.payer_id]["paid"] += sett.amount
            if sett.receiver_id in balances_tracker:
                balances_tracker[sett.receiver_id]["owed"] += sett.amount

        # 4. Compile individual summaries
        balances_list = []
        for uid, track in balances_tracker.items():
            user_obj = members_map[uid]
            paid = track["paid"]
            owed = track["owed"]
            net_balance = paid - owed

            balances_list.append(
                MemberBalanceSummary(
                    user_id=uid,
                    full_name=user_obj.full_name,
                    email=user_obj.email,
                    total_paid=paid,
                    total_owed=owed,
                    net_balance=net_balance,
                )
            )

        # 5. Simplify Debt Transactions
        simplified_debts = BalanceService.simplify_debts(balances_list)

        return GroupBalanceResponse(
            group_id=group_id,
            total_expenses=total_expenses,
            balances=balances_list,
            simplified_debts=simplified_debts,
        )

    @staticmethod
    def simplify_debts(balances: list[MemberBalanceSummary]) -> list[SimplifiedDebt]:
        # Filter into positive and negative balances
        creditors = []
        debtors = []

        for b in balances:
            if b.net_balance > Decimal("0.005"):
                creditors.append({"id": b.user_id, "name": b.full_name, "bal": b.net_balance})
            elif b.net_balance < Decimal("-0.005"):
                debtors.append({"id": b.user_id, "name": b.full_name, "bal": -b.net_balance})

        simplified = []

        # Greedy match largest creditor with largest debtor
        while creditors and debtors:
            creditors.sort(key=lambda x: x["bal"], reverse=True)
            debtors.sort(key=lambda x: x["bal"], reverse=True)

            c = creditors[0]
            d = debtors[0]

            amount = min(c["bal"], d["bal"])
            if amount > Decimal("0.00"):
                simplified.append(
                    SimplifiedDebt(
                        from_user_id=d["id"],
                        from_user_name=d["name"],
                        to_user_id=c["id"],
                        to_user_name=c["name"],
                        amount=amount.quantize(Decimal("0.01")),
                    )
                )
                c["bal"] -= amount
                d["bal"] -= amount

            if c["bal"] < Decimal("0.005"):
                creditors.pop(0)
            if d["bal"] < Decimal("0.005"):
                debtors.pop(0)

        return simplified


balance_service = BalanceService()
