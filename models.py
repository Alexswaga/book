from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    books = relationship("Book", back_populates="owner")
    reading_progresses = relationship("ReadingProgress", back_populates="user")
    reviews = relationship("Review", back_populates="user")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    description = Column(String, nullable=True)
    total_pages = Column(Integer, nullable=False)
    pdf_path = Column(String, nullable=True)  # путь к PDF файлу
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    owner = relationship("User", back_populates="books")
    reading_progress = relationship("ReadingProgress", back_populates="book", uselist=False)
    reviews = relationship("Review", back_populates="book")

class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    current_page = Column(Integer, nullable=False, default=0)
    is_finished = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="reading_progresses")
    book = relationship("Book", back_populates="reading_progress")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")
