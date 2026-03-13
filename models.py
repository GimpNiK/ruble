from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum
import hashlib
import os
import json 


class JsonDict:
    """Словарь, который автоматически сохраняется в JSON файл при изменениях"""
    
    def __init__(self, filename: str, auto_save: bool = True):
        self.filename = filename
        self.auto_save = auto_save
        self.data = self.load()
    
    def load(self) -> dict:
        """Загружает данные из JSON файла"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("{}")
            return {}
    
    def save(self):
        """Сохраняет данные в JSON файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
        if self.auto_save:
            self.save()
    
    def __delitem__(self, key):
        del self.data[key]
        if self.auto_save:
            self.save()
    
    def __contains__(self, key):
        return key in self.data
    
    def __len__(self):
        return len(self.data)
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def update(self, *args, **kwargs):
        self.data.update(*args, **kwargs)
        if self.auto_save:
            self.save()
    
    def keys(self):
        return self.data.keys()
    
    def values(self):
        return self.data.values()
    
    def items(self):
        return self.data.items()

Base = declarative_base()

config = JsonDict("config.json")
engine = create_engine('sqlite:///finance.db', echo=False)
Session = sessionmaker(bind=engine)
db = Session()  


class FormatPeriod(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"



def is_registered():
    return config.get('password') or False
def check_password(password):
    return config.get('password',"") == hashlib.sha256(password.encode()).hexdigest()
      
def set_password(password):
    config["password"] = hashlib.sha256(password.encode()).hexdigest()


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    name = Column(Text(1024))
    sum = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.now)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category")

class RegularTransaction(Base):
    __tablename__ = 'regular_transactions'
    id = Column(Integer, primary_key=True)
    name = Column(Text(1024))
    format_period = Column(Enum(FormatPeriod))
    start_date = Column(Integer)
    numdays =Column(Integer)
    sum = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category")

    def run(self):
        session = Session()
        transaction = Transaction(
            name = self.name,
            sum = self.sum,
            date = datetime.now(),
            category_id = self.category_id
            )
        session.add(transaction)
        session.commit()
        session.close()

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    reg_transaction_id = Column(Integer, ForeignKey('regular_transactions.id'))  
    reg_transaction = relationship("RegularTransaction")



def create_database(db_path='sqlite:///finance.db', drop_existing=True):
    import os
    if drop_existing and db_path.startswith('sqlite:///'):
        db_file = db_path.replace('sqlite:///', '')
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Существующая БД {db_file} удалена")
    
    engine = create_engine(db_path, echo=False)
    

    Base.metadata.create_all(engine)
    print(f"База данных создана: {db_path}")
    
    return engine

def get_balance():
    result = db.query(func.sum(Transaction.sum)).scalar()
    return result if result is not None else 0

def get_monthly_profit():
    now = datetime.now()
    first_day = datetime(now.year, now.month, 1)
    
    result = db.query(func.sum(Transaction.sum)).filter(
        Transaction.date >= first_day
    ).scalar()
    return result if result is not None else 0
#     def when_run(self):
        
# 
# def get_categories():
#     session = Session()
#     categories = session.query(Category).all()
#     return {c.id:c.name for c in categories}
# def get_transactins():
#     session = Session()
#     categories = session.query(Transaction).all()
#     return {c.id:{"id":c.id,"" for c in categories}
# def create_transaction():
#     ...
# def create
