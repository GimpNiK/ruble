from datetime import datetime, timedelta
from calendar import monthrange
import enum
import hashlib
import json
import os

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from notify import send_notification

Base = declarative_base()

DEFAULT_CATEGORIES = [
    ("Зарплата", "income"),
    ("Подработка", "income"),
    ("Подарки", "income"),
    ("Продукты", "expense"),
    ("Транспорт", "expense"),
    ("Жильё", "expense"),
    ("Развлечения", "expense"),
    ("Здоровье", "expense"),
    ("Образование", "expense"),
    ("Прочее", "expense"),
]

NOTIFY_DAYS_DEFAULT = 3


class JsonDict:
    """Словарь с автосохранением в JSON."""

    def __init__(self, filename: str, auto_save: bool = True):
        self.filename = filename
        self.auto_save = auto_save
        self.data = self.load()

    def load(self) -> dict:
        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write("{}")
        return {}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        if self.auto_save:
            self.save()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __contains__(self, key):
        return key in self.data


class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class FormatPeriod(enum.Enum):
    DAILY = "Ежедневно"
    WEEKLY = "Еженедельно"
    MONTHLY = "Ежемесячно"
    QUARTERLY = "Ежеквартально"
    YEARLY = "Ежегодно"
    CUSTOM = "Произвольно"


config = JsonDict("config.json")
engine = create_engine("sqlite:///finance.db", echo=False)
Session = sessionmaker(bind=engine)
db = Session()


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False, default=TransactionType.EXPENSE)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    sum = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.now)
    transaction_type = Column(Enum(TransactionType), nullable=False, default=TransactionType.EXPENSE)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category")

    @property
    def signed_sum(self) -> float:
        return self.sum if self.transaction_type == TransactionType.INCOME else -self.sum


class RegularTransaction(Base):
    __tablename__ = "regular_transactions"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)
    format_period = Column(Enum(FormatPeriod), default=FormatPeriod.MONTHLY)
    start_date = Column(DateTime, default=datetime.now)
    numdays = Column(Integer, default=30)
    notify_days = Column(Integer, default=NOTIFY_DAYS_DEFAULT)
    sum = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False, default=TransactionType.EXPENSE)
    is_active = Column(Integer, default=1)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category")
    
    notifications = relationship(
        "Notification",
        back_populates="regular",
        cascade="all, delete-orphan"
    )

    def next_due_date(self, reference: datetime | None = None) -> datetime:
        ref = reference or datetime.now()
        start = self.start_date or ref

        if self.format_period == FormatPeriod.DAILY:
            delta = timedelta(days=1)
        elif self.format_period == FormatPeriod.WEEKLY:
            delta = timedelta(weeks=1)
        elif self.format_period == FormatPeriod.MONTHLY:
            delta = None
        elif self.format_period == FormatPeriod.QUARTERLY:
            delta = None
        elif self.format_period == FormatPeriod.YEARLY:
            delta = None
        else:
            delta = timedelta(days=max(self.numdays or 1, 1))

        if delta is not None:
            due = start
            while due.date() < ref.date():
                due += delta
            return due

        due = start
        while due.date() < ref.date():
            if self.format_period == FormatPeriod.MONTHLY:
                month = due.month + 1
                year = due.year
                if month > 12:
                    month = 1
                    year += 1
                day = min(due.day, monthrange(year, month)[1])
                due = due.replace(year=year, month=month, day=day)
            elif self.format_period == FormatPeriod.QUARTERLY:
                month = due.month + 3
                year = due.year
                while month > 12:
                    month -= 12
                    year += 1
                day = min(due.day, monthrange(year, month)[1])
                due = due.replace(year=year, month=month, day=day)
            else:
                due = due.replace(year=due.year + 1)
        return due


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    sum = Column(Float, nullable=False)
    descr = Column(Text)
    regular_transaction_id = Column(Integer, ForeignKey("regular_transactions.id", ondelete="CASCADE"))
    
    regular = relationship("RegularTransaction", back_populates="notifications")


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    target_sum = Column(Float, nullable=False)
    current_sum = Column(Float, default=0)
    deadline = Column(DateTime)


def is_registered() -> bool:
    return bool(config.get("password"))


def check_password(password: str) -> bool:
    return config.get("password", "") == hashlib.sha256(password.encode()).hexdigest()


def set_password(password: str):
    config["password"] = hashlib.sha256(password.encode()).hexdigest()


def init_engine(db_path: str = "sqlite:///finance.db"):
    global engine, Session, db
    engine = create_engine(db_path, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()


def create_database(db_path: str = "sqlite:///finance.db", drop_existing: bool = False):
    if drop_existing and db_path.startswith("sqlite:///"):
        db_file = db_path.replace("sqlite:///", "")
        if os.path.exists(db_file):
            os.remove(db_file)

    init_engine(db_path)
    Base.metadata.create_all(engine)
    _seed_categories()
    return engine


def _seed_categories():
    if db.query(Category).count() > 0:
        return
    for name, ttype in DEFAULT_CATEGORIES:
        db.add(Category(name=name, transaction_type=TransactionType(ttype)))
    db.commit()


def get_balance() -> float:
    income = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
        Transaction.transaction_type == TransactionType.INCOME
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
        Transaction.transaction_type == TransactionType.EXPENSE
    ).scalar()
    return float(income or 0) - float(expense or 0)


def get_monthly_profit() -> float:
    now = datetime.now()
    first_day = datetime(now.year, now.month, 1)
    income = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
        Transaction.date >= first_day,
        Transaction.transaction_type == TransactionType.INCOME,
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
        Transaction.date >= first_day,
        Transaction.transaction_type == TransactionType.EXPENSE,
    ).scalar()
    return float(income or 0) - float(expense or 0)


def get_transactions(start: datetime, end: datetime):
    return (
        db.query(Transaction)
        .filter(Transaction.date >= start, Transaction.date <= end)
        .order_by(Transaction.date.desc())
        .all()
    )


def get_expenses_by_category(start: datetime, end: datetime) -> list[tuple[str, float]]:
    rows = (
        db.query(Category.name, func.sum(Transaction.sum))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.transaction_type == TransactionType.EXPENSE,
        )
        .group_by(Category.name)
        .all()
    )
    return [(name, float(total or 0)) for name, total in rows]


def get_daily_totals(start: datetime, end: datetime) -> tuple[list[str], list[float], list[float]]:
    days = []
    income_vals = []
    expense_vals = []
    current = start.date()
    end_date = end.date()
    while current <= end_date:
        day_start = datetime.combine(current, datetime.min.time())
        day_end = datetime.combine(current, datetime.max.time())
        income = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
            Transaction.date >= day_start,
            Transaction.date <= day_end,
            Transaction.transaction_type == TransactionType.INCOME,
        ).scalar()
        expense = db.query(func.coalesce(func.sum(Transaction.sum), 0)).filter(
            Transaction.date >= day_start,
            Transaction.date <= day_end,
            Transaction.transaction_type == TransactionType.EXPENSE,
        ).scalar()
        days.append(current.strftime("%d.%m"))
        income_vals.append(float(income or 0))
        expense_vals.append(float(expense or 0))
        current += timedelta(days=1)
    return days, income_vals, expense_vals


def sync_payment_notifications():
    """Создаёт напоминания о постоянных платежах за N дней до срока."""
    today = datetime.now().date()
    for regular in db.query(RegularTransaction).filter(RegularTransaction.is_active == 1).all():
        due = regular.next_due_date().date()
        
        if due >= today:
            notify_from = due - timedelta(days=regular.notify_days or NOTIFY_DAYS_DEFAULT)
            if notify_from <= today:
                exists = (
                    db.query(Notification)
                    .filter(
                        Notification.regular_transaction_id == regular.id,
                        func.date(Notification.date) == due,
                    )
                    .first()
                )
                if not exists:
                    sign = "+" if regular.transaction_type == TransactionType.INCOME else "-"
                    db.add(
                        Notification(
                            date=datetime.combine(due, datetime.min.time()),
                            sum=regular.sum,
                            descr=f"{sign} {regular.name or 'Платёж'} — {regular.description or ''}".strip(),
                            regular_transaction_id=regular.id,
                        )
                    )
                    send_notification(
                        f"Напоминание: {regular.name}",
                        f"{sign} {regular.sum:.2f} ₽. Срок {due.strftime('%d.%m.%Y')}"
                    )
    db.commit()


def get_categories(transaction_type: TransactionType | None = None):
    query = db.query(Category)
    if transaction_type:
        query = query.filter(Category.transaction_type == transaction_type)
    return query.order_by(Category.name).all()


def add_transaction(name, amount, category_id, transaction_type, date=None):
    transaction = Transaction(
        name=name,
        sum=float(amount),
        category_id=category_id,
        transaction_type=transaction_type,
        date=date or datetime.now(),
    )
    db.add(transaction)
    db.commit()
    return transaction


def add_regular_transaction(**kwargs):
    regular = RegularTransaction(**kwargs)
    db.add(regular)
    db.commit()
    sync_payment_notifications()
    return regular


def add_financial_goal(name, target_sum, deadline=None, description="", current_sum=0):
    goal = FinancialGoal(
        name=name,
        target_sum=float(target_sum),
        current_sum=float(current_sum),
        deadline=deadline,
        description=description,
    )
    db.add(goal)
    db.commit()
    return goal


def delete_by_model(model, item_id):
    item = db.query(model).get(item_id)
    if item:
        db.delete(item)
        db.commit()


def get_financial_goals():
    """Возвращает все финансовые цели, отсортированные по дате создания (сначала новые)."""
    return db.query(FinancialGoal).order_by(FinancialGoal.id.desc()).all()