from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    email: str

class BookBase(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    total_pages: int

class ReviewBase(BaseModel):
    rating: int
    text: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class BookCreate(BookBase):
    pass

class ReadingProgressCreate(BaseModel):
    current_page: int

class ReviewCreate(ReviewBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime

class BookResponse(BookBase):
    id: int
    owner_id: int
    created_at: datetime

class ReadingProgressResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    current_page: int
    is_finished: bool
    updated_at: datetime

class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None