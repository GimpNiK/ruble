from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker,Session
import enum

Base = declarative_base()
class FormatPeriod(enum.Enum):
    ...

class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True, default=1)
    _password = Column(String(128))
    currency = Column(String(3), default='RUB')
    @staticmethod
    def register(**kw):
        session = Session()
        settings = Settings(id = 1,**kw)
        session.add(settings)
        session.commit()
    @staticmethod
    def check_password(password):
        session = Session()
        settings = session.query(Settings).first()
        if settings and settings._password == hash(password):
            session.close()
            return True
        else:
            session.close()
            return False
    @staticmethod
    def set_password(password):
        session = Session()
        settings = Settings(id = 1,_password = password)
        session.add(settings)
        session.commit()


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
    def when_run(self):
        
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
def get_categories():
    session = Session()
    categories = session.query(Category).all()
    return {c.id:c.name for c in categories}
def get_transactins():
    session = Session()
    categories = session.query(Transaction).all()
    return {c.id:{"id":c.id,"" for c in categories}
def create_transaction():
    ...
def create
