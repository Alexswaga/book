from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class BookBase(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    total_pages: int
    pdf_path: Optional[str] = None

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

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookResponse(BookBase):
    id: int
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReadingProgressResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    current_page: int
    is_finished: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
