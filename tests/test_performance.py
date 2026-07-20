import timeit
import random
from datetime import datetime, timedelta
import os
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Category, Transaction, TransactionType, add_transaction,
    get_transactions, get_expenses_by_category, get_balance, db
)
from crypto_utils import encrypt_database, decrypt_database


def setup_large_db():
    """Создаёт 1000 транзакций для замера."""
    cat_income = db.query(Category).filter_by(name="Зарплата").first()
    cat_expense = db.query(Category).filter_by(name="Продукты").first()
    start = datetime.now() - timedelta(days=365)
    for i in range(1000):
        date = start + timedelta(days=random.randint(0, 365))
        ttype = random.choice([TransactionType.INCOME, TransactionType.EXPENSE])
        cat = cat_income if ttype == TransactionType.INCOME else cat_expense
        add_transaction(
            name=f"Тест {i}",
            amount=random.randint(100, 10000),
            category_id=cat.id,
            transaction_type=ttype,
            date=date
        )


def bench_query():
    start = datetime.now() - timedelta(days=30)
    end = datetime.now()
    get_transactions(start, end)


def bench_crypto():
    temp_dir = tempfile.mkdtemp()
    plain = os.path.join(temp_dir, "test.db")
    enc = os.path.join(temp_dir, "test.db.enc")
    # Создаём тестовый файл ~10 МБ
    with open(plain, "wb") as f:
        f.write(b"0" * 10_000_000)  # 10 MB
    password = "1234"
    # Замеряем шифрование
    encrypt_time = timeit.timeit(
        lambda: encrypt_database(password, plain_path=plain, enc_path=enc),
        number=1
    )
    # Замеряем дешифрование
    decrypt_time = timeit.timeit(
        lambda: decrypt_database(password, enc_path=enc, plain_path=plain),
        number=1
    )
    # Очистка
    os.remove(enc)
    os.remove(plain)
    os.rmdir(temp_dir)
    return encrypt_time, decrypt_time


if __name__ == '__main__':
    # Запуск бенчмарка
    import time
    print("Создание тестовых данных...")
    setup_large_db()
    print("Замер запроса транзакций:")
    print(timeit.timeit(bench_query, number=10) / 10, "секунд в среднем")
    print("Замер шифрования/дешифрования 10 МБ:")
    enc_t, dec_t = bench_crypto()
    print(f"Шифрование: {enc_t:.2f} сек, дешифрование: {dec_t:.2f} сек")