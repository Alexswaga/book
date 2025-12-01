from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import models
import schemas
from database import engine, get_db
from typing import List

# Секретный ключ для JWT
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Создание таблиц
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Tracker API")

# CORS для PythonAnywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Зависимости
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Вспомогательные функции
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Главная страница - веб-интерфейс
@app.get("/")
async def read_root():
    return FileResponse("templates/index.html")

# Регистрация
@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Авторизация
@app.post("/login")
def login(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Книги
@app.post("/books", response_model=schemas.BookResponse)
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_book = models.Book(
        title=book.title,
        author=book.author,
        description=book.description,
        total_pages=book.total_pages,
        owner_id=current_user.id
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/books", response_model=List[schemas.BookResponse])
def read_books(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    books = db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()
    return books

# Прогресс чтения
@app.post("/books/{book_id}/progress", response_model=schemas.ReadingProgressResponse)
def update_progress(book_id: int, progress: schemas.ReadingProgressCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Проверяем что книга принадлежит пользователю
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.owner_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Ищем существующий прогресс
    db_progress = db.query(models.ReadingProgress).filter(
        models.ReadingProgress.book_id == book_id,
        models.ReadingProgress.user_id == current_user.id
    ).first()
    
    if db_progress:
        # Обновляем существующий
        db_progress.current_page = progress.current_page
        db_progress.is_finished = progress.current_page >= book.total_pages
    else:
        # Создаем новый
        db_progress = models.ReadingProgress(
            user_id=current_user.id,
            book_id=book_id,
            current_page=progress.current_page,
            is_finished=progress.current_page >= book.total_pages
        )
        db.add(db_progress)
    
    db.commit()
    db.refresh(db_progress)
    return db_progress

@app.get("/books/{book_id}/progress", response_model=schemas.ReadingProgressResponse)
def get_progress(book_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    progress = db.query(models.ReadingProgress).filter(
        models.ReadingProgress.book_id == book_id,
        models.ReadingProgress.user_id == current_user.id
    ).first()
    
    if not progress:
        # Возвращаем прогресс по умолчанию
        return schemas.ReadingProgressResponse(
            id=0,
            user_id=current_user.id,
            book_id=book_id,
            current_page=0,
            is_finished=False,
            updated_at=datetime.utcnow()
        )
    
    return progress

# Рецензии
@app.post("/books/{book_id}/reviews", response_model=schemas.ReviewResponse)
def create_review(book_id: int, review: schemas.ReviewCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Проверяем что книга принадлежит пользователю
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.owner_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db_review = models.Review(
        user_id=current_user.id,
        book_id=book_id,
        rating=review.rating,
        text=review.text
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

# Для PythonAnywhere
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)