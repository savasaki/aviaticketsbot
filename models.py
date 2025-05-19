from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    language = Column(String, default='ru')
    currency = Column(String, default='RUB')
    timezone = Column(String, default='Europe/Moscow')
    passengers_default = Column(Integer, default=1)
    direct_only_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    search_history = relationship("SearchHistory", back_populates="user")
    tracked_routes = relationship("TrackedRoute", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    origin_city = Column(String)
    destination_city = Column(String)
    depart_date = Column(String) 
    passengers = Column(Integer)
    direct_only = Column(Boolean)
    search_time = Column(DateTime, default=datetime.utcnow)
    
    results = relationship("SearchResult", back_populates="search", cascade="all, delete-orphan")
    user = relationship("User", back_populates="search_history")

class SearchResult(Base):
    __tablename__ = 'search_results'

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey('search_history.id'))
    airline_code = Column(String)
    departure_date = Column(Date)
    price = Column(Integer)
    currency = Column(String)
    link = Column(String)

    search = relationship("SearchHistory", back_populates="results")

class TrackedRoute(Base):
    __tablename__ = 'tracked_routes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    currency = Column(String, default='RUB')
    origin_city = Column(String)
    destination_city = Column(String)
    depart_date = Column(String)  
    notify_below_price = Column(Integer, nullable=True)
    price_drop_percent = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_notified_price = Column(Integer, nullable=True)
    last_notified_percent = Column(Integer, nullable=True)
    last_checked_price = Column(Integer, nullable=True)

    user = relationship("User", back_populates="tracked_routes")

class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedbacks")

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    route_id = Column(Integer, ForeignKey('tracked_routes.id'), nullable=True)
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

class Airline(Base):
    __tablename__ = 'airlines'

    code = Column(String, primary_key=True)
    name_ru = Column(String)
    name_en = Column(String)
    country = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)

class Currency(Base):
    __tablename__ = 'currencies'

    code = Column(String, primary_key=True)
    name = Column(String)
    symbol = Column(String)
    flag = Column(String)

class Translation(Base):
    __tablename__ = 'translations'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    lang = Column(String)
    value = Column(Text)
