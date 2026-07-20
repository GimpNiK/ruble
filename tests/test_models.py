import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch
import warnings
warnings.simplefilter("ignore", ResourceWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Category, Transaction, RegularTransaction, Notification, FinancialGoal,
    TransactionType, FormatPeriod,
    get_balance, get_monthly_profit, get_transactions, get_expenses_by_category,
    get_daily_totals,  # добавлен прямой импорт
    add_transaction, add_regular_transaction, add_financial_goal,
    delete_by_model, sync_payment_notifications, get_financial_goals,
    get_categories, db
)


class TestModels(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self._old_db = db
        import models
        models.db = self.session
        self._seed_categories()

    def tearDown(self):
        try:
            self.session.rollback()
        except:
            pass
        self.session.close()
        self.engine.dispose()   # закрывает все соединения
        import models
        models.db = self._old_db

    def _seed_categories(self):
        cats = [
            Category(name="Зарплата", transaction_type=TransactionType.INCOME),
            Category(name="Продукты", transaction_type=TransactionType.EXPENSE),
            Category(name="Прочее", transaction_type=TransactionType.EXPENSE),
        ]
        self.session.add_all(cats)
        self.session.commit()

    def test_add_transaction(self):
        cat = self.session.query(Category).filter_by(name="Зарплата").first()
        t = add_transaction("Тест", 1000, cat.id, TransactionType.INCOME)
        self.assertIsNotNone(t.id)
        self.assertEqual(t.sum, 1000)
        self.assertEqual(t.transaction_type, TransactionType.INCOME)

    def test_get_balance(self):
        cat_inc = self.session.query(Category).filter_by(name="Зарплата").first()
        cat_exp = self.session.query(Category).filter_by(name="Продукты").first()
        add_transaction("ЗП", 5000, cat_inc.id, TransactionType.INCOME)
        add_transaction("Еда", 1500, cat_exp.id, TransactionType.EXPENSE)
        balance = get_balance()
        self.assertEqual(balance, 3500.0)

    def test_get_monthly_profit(self):
        now = datetime.now()
        first_day = datetime(now.year, now.month, 1)
        cat_inc = self.session.query(Category).filter_by(name="Зарплата").first()
        cat_exp = self.session.query(Category).filter_by(name="Продукты").first()
        add_transaction("ЗП", 5000, cat_inc.id, TransactionType.INCOME, date=first_day + timedelta(days=5))
        add_transaction("Еда", 1000, cat_exp.id, TransactionType.EXPENSE, date=first_day + timedelta(days=10))
        last_month = first_day - timedelta(days=1)
        add_transaction("Старая", 200, cat_exp.id, TransactionType.EXPENSE, date=last_month)
        profit = get_monthly_profit()
        self.assertEqual(profit, 4000.0)

    def test_get_transactions(self):
        start = datetime.now() - timedelta(days=10)
        end = datetime.now()
        cat_inc = self.session.query(Category).filter_by(name="Зарплата").first()
        cat_exp = self.session.query(Category).filter_by(name="Продукты").first()
        add_transaction("ЗП", 5000, cat_inc.id, TransactionType.INCOME, date=start + timedelta(days=2))
        add_transaction("Еда", 1000, cat_exp.id, TransactionType.EXPENSE, date=end - timedelta(days=1))
        txs = get_transactions(start, end)
        self.assertEqual(len(txs), 2)

    def test_get_expenses_by_category(self):
        start = datetime.now() - timedelta(days=10)
        end = datetime.now()
        cat1 = self.session.query(Category).filter_by(name="Продукты").first()
        cat2 = self.session.query(Category).filter_by(name="Прочее").first()
        add_transaction("Еда1", 500, cat1.id, TransactionType.EXPENSE, date=start + timedelta(days=1))
        add_transaction("Еда2", 300, cat1.id, TransactionType.EXPENSE, date=start + timedelta(days=2))
        add_transaction("Прочее", 200, cat2.id, TransactionType.EXPENSE, date=start + timedelta(days=3))
        data = get_expenses_by_category(start, end)
        data_dict = dict(data)
        self.assertEqual(data_dict.get("Продукты", 0), 800.0)
        self.assertEqual(data_dict.get("Прочее", 0), 200.0)

    def test_sync_payment_notifications(self):
        cat_exp = self.session.query(Category).filter_by(name="Продукты").first()
        reg = RegularTransaction(
            name="Интернет",
            sum=1000,
            start_date=datetime.now() + timedelta(days=1),
            format_period=FormatPeriod.MONTHLY,
            notify_days=2,
            transaction_type=TransactionType.EXPENSE,
            category_id=cat_exp.id,
            is_active=1
        )
        self.session.add(reg)
        self.session.commit()
        with patch('models.send_notification') as mock_notify:
            sync_payment_notifications()
            notifs = self.session.query(Notification).filter_by(regular_transaction_id=reg.id).all()
            self.assertEqual(len(notifs), 1)
            self.assertAlmostEqual(notifs[0].sum, 1000)
            mock_notify.assert_called_once()

    def test_financial_goal(self):
        goal = add_financial_goal("Новый телефон", 50000, current_sum=10000)
        self.assertIsNotNone(goal.id)
        goals = get_financial_goals()
        self.assertEqual(len(goals), 1)
        self.assertEqual(goals[0].name, "Новый телефон")
        delete_by_model(FinancialGoal, goal.id)
        self.assertEqual(self.session.query(FinancialGoal).count(), 0)

    def test_get_categories(self):
        cats = get_categories(TransactionType.EXPENSE)
        self.assertTrue(len(cats) > 0)
        self.assertTrue(any(c.name == "Продукты" for c in cats))
        cats_income = get_categories(TransactionType.INCOME)
        self.assertTrue(any(c.name == "Зарплата" for c in cats_income))

    def test_get_daily_totals(self):
        start = datetime.now() - timedelta(days=5)
        end = datetime.now()
        days, incomes, expenses = get_daily_totals(start, end)
        self.assertEqual(len(days), 6)
        self.assertEqual(len(incomes), len(days))
        self.assertEqual(len(expenses), len(days))


if __name__ == '__main__':
    unittest.main()