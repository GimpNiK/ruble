"""Шифрование локальной базы данных с ключом, производным от PIN-кода."""
import base64
import os
import time

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT = b"ruble_finance_v1"
PLAIN_DB = "finance.db"
ENCRYPTED_DB = "finance.db.enc"


def derive_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=120_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_database(password: str, plain_path: str = PLAIN_DB, enc_path: str = ENCRYPTED_DB) -> None:
    if not os.path.exists(plain_path):
        return
    
    fernet = Fernet(derive_key(password))
    
    # Читаем и шифруем
    with open(plain_path, "rb") as src:
        encrypted = fernet.encrypt(src.read())
    
    with open(enc_path, "wb") as dst:
        dst.write(encrypted)
    
    # Даём время на закрытие файлов
    time.sleep(0.5)
    
    # Удаляем файл с повторными попытками
    for attempt in range(5):
        try:
            os.remove(plain_path)
            break
        except PermissionError:
            time.sleep(0.5)
            continue
        except Exception:
            break


def decrypt_database(password: str, enc_path: str = ENCRYPTED_DB, plain_path: str = PLAIN_DB) -> bool:
    if not os.path.exists(enc_path):
        return True
    fernet = Fernet(derive_key(password))
    try:
        with open(enc_path, "rb") as src:
            decrypted = fernet.decrypt(src.read())
    except InvalidToken:
        return False
    with open(plain_path, "wb") as dst:
        dst.write(decrypted)
    return True


def remove_plain_database(plain_path: str = PLAIN_DB) -> None:
    if os.path.exists(plain_path):
        try:
            os.remove(plain_path)
        except PermissionError:
            time.sleep(0.5)
            try:
                os.remove(plain_path)
            except:
                pass