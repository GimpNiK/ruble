"""Базовые тесты модели данных."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from models import (
    Base,
    Category,
    FinancialGoal,
    FormatPeriod,
    RegularTransaction,
    Transaction,
    TransactionType,
    get_balance,
    get_expenses_by_category,
    get_monthly_profit,
)


class ModelsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = f"sqlite:///{self.tmp.name}"
        self.engine = create_engine(self.db_path)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        models.engine = self.engine
        models.Session = sessionmaker(bind=self.engine)
        models.db = self.session

        cat_income = Category(name="Зарплата", transaction_type=TransactionType.INCOME)
        cat_expense = Category(name="Еда", transaction_type=TransactionType.EXPENSE)
        self.session.add_all([cat_income, cat_expense])
        self.session.commit()
        self.income_id = cat_income.id
        self.expense_id = cat_expense.id

    def tearDown(self):
        self.session.close()
        models.engine.dispose()
        os.unlink(self.tmp.name)

    def test_balance_and_monthly_profit(self):
        self.session.add_all(
            [
                Transaction(sum=1000, transaction_type=TransactionType.INCOME, category_id=self.income_id),
                Transaction(sum=300, transaction_type=TransactionType.EXPENSE, category_id=self.expense_id),
            ]
        )
        self.session.commit()
        self.assertEqual(get_balance(), 700)
        self.assertEqual(get_monthly_profit(), 700)

    def test_expenses_by_category(self):
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)
        self.session.add(
            Transaction(
                sum=150,
                transaction_type=TransactionType.EXPENSE,
                category_id=self.expense_id,
                date=datetime.now(),
            )
        )
        self.session.commit()
        data = get_expenses_by_category(start, end)
        self.assertEqual(data, [("Еда", 150.0)])

    def test_regular_next_due_date(self):
        regular = RegularTransaction(
            name="Аренда",
            sum=20000,
            format_period=FormatPeriod.MONTHLY,
            start_date=datetime(2025, 1, 15),
            category_id=self.expense_id,
            transaction_type=TransactionType.EXPENSE,
        )
        due = regular.next_due_date(datetime(2025, 3, 10))
        self.assertEqual(due.month, 3)
        self.assertEqual(due.day, 15)

    def test_financial_goal(self):
        goal = FinancialGoal(name="Отпуск", target_sum=50000, current_sum=10000)
        self.session.add(goal)
        self.session.commit()
        saved = self.session.query(FinancialGoal).first()
        self.assertEqual(saved.name, "Отпуск")
        self.assertEqual(saved.target_sum, 50000)


if __name__ == "__main__":
    unittest.main()
