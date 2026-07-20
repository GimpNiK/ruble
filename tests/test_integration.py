import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch
import warnings
# Подавление ResourceWarning для чистоты вывода
warnings.simplefilter("ignore", ResourceWarning)

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Category, RegularTransaction, Notification, TransactionType, FormatPeriod,
    add_regular_transaction, delete_by_model, sync_payment_notifications, db,
    FinancialGoal, add_financial_goal, get_financial_goals
)


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        import models
        self._old_db = models.db
        models.db = self.session
        self._seed_categories()
        self.notify_patcher = patch('models.send_notification')
        self.mock_notify = self.notify_patcher.start()

    def tearDown(self):
        # Откат возможных изменений
        try:
            self.session.rollback()
        except:
            pass
        self.notify_patcher.stop()
        self.session.close()
        # Явно закрываем все соединения движка
        self.engine.dispose()
        import models
        models.db = self._old_db

    def _seed_categories(self):
        cats = [
            Category(name="Зарплата", transaction_type=TransactionType.INCOME),
            Category(name="Продукты", transaction_type=TransactionType.EXPENSE),
        ]
        self.session.add_all(cats)
        self.session.commit()

    def test_full_regular_flow(self):
        cat = self.session.query(Category).filter_by(name="Продукты").first()
        reg = add_regular_transaction(
            name="Интернет",
            sum=1000,
            start_date=datetime.now() + timedelta(days=1),
            notify_days=1,
            format_period=FormatPeriod.MONTHLY,
            transaction_type=TransactionType.EXPENSE,
            category_id=cat.id
        )
        notifs = self.session.query(Notification).filter_by(regular_transaction_id=reg.id).all()
        self.assertEqual(len(notifs), 1)
        self.mock_notify.assert_called()

        delete_by_model(RegularTransaction, reg.id)
        notifs_after = self.session.query(Notification).filter_by(regular_transaction_id=reg.id).all()
        self.assertEqual(len(notifs_after), 0)

    def test_goal_flow(self):
        goal = add_financial_goal("Тест", 10000, current_sum=5000)
        self.assertIsNotNone(goal.id)
        goals = get_financial_goals()
        self.assertEqual(len(goals), 1)
        delete_by_model(FinancialGoal, goal.id)
        self.assertEqual(self.session.query(FinancialGoal).count(), 0)


if __name__ == '__main__':
    unittest.main()