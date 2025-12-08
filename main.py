from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
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
        
        # Дополнительная проверка и исправление структуры БД
try:
    from check_and_fix_db import check_and_fix_database
    check_and_fix_database()
except ImportError:
    print("⚠️  Модуль check_and_fix_db не найден")
except Exception as e:
    print(f"⚠️  Ошибка при проверке структуры БД: {e}")

app = FastAPI(title="Book Tracker API")

# CORS для PythonAnywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== ИСПРАВЛЕННАЯ КОНФИГУРАЦИЯ ХЕШИРОВАНИЯ =====
# Используем sha256_crypt для совместимости с существующими хешами
pwd_context = CryptContext(
    schemes=["sha256_crypt", "bcrypt"],  # Сначала пробуем sha256_crypt, потом bcrypt
    deprecated="auto",
    sha256_crypt__default_rounds=535000  # Совпадает с вашими хешами ($5$rounds=535000$...)
)

# Зависимости
security = HTTPBearer()

# Вспомогательные функции
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Теперь будет создавать sha256_crypt хеши
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
    # Generate email if not provided
    if user.email is None or user.email == "":
        user.email = f"{user.username}@booktracker.local"
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

# Выход из системы
@app.post("/logout")
def logout(token: HTTPAuthorizationCredentials = Depends(security)):
    """
    Выход из системы.
    На клиенте нужно удалить токен из localStorage.
    """
    # В этой простой реализации просто подтверждаем выход
    # В production можно добавить токен в черный список
    return {"message": "Successfully logged out", "success": True}

# Получить информацию о текущем пользователе
@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# Книги
@app.post("/books", response_model=schemas.BookResponse)
async def create_book(
    title: str = Form(...),
    author: str = Form(...),
    description: Optional[str] = Form(None),
    total_pages: int = Form(...),
    pdf_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Сохраняем PDF если есть
    pdf_path = None
    if pdf_file and pdf_file.filename:
        import os
        import uuid
        # Создаем папку если нет
        os.makedirs("uploads/pdf", exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_ext = os.path.splitext(pdf_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        pdf_path = os.path.join("uploads/pdf", unique_filename)
        
        # Сохраняем файл
        with open(pdf_path, "wb") as buffer:
            content = await pdf_file.read()
            buffer.write(content)
    
    # Создаём книгу
    db_book = models.Book(
        title=title,
        author=author,
        description=description,
        total_pages=total_pages,
        pdf_path=pdf_path,  # сохраняем путь к PDF
        owner_id=current_user.id,
        created_at=datetime.now()
    )
    
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/books", response_model=List[schemas.BookResponse])
def get_books(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Получить все книги текущего пользователя"""
    books = db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()
    return books

# Получить одну книгу
@app.get("/books/{book_id}", response_model=schemas.BookResponse)
def read_book(book_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    book = db.query(models.Book).filter(
        models.Book.id == book_id, 
        models.Book.owner_id == current_user.id
    ).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

# Обновить книгу
@app.put("/books/{book_id}", response_model=schemas.BookResponse)
def update_book(book_id: int, book_update: schemas.BookCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    book = db.query(models.Book).filter(
        models.Book.id == book_id, 
        models.Book.owner_id == current_user.id
    ).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Обновляем поля
    book.title = book_update.title
    book.author = book_update.author
    book.description = book_update.description
    book.total_pages = book_update.total_pages
    
    db.commit()
    db.refresh(book)
    return book

# Удалить книгу
@app.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    book = db.query(models.Book).filter(
        models.Book.id == book_id, 
        models.Book.owner_id == current_user.id
    ).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully", "success": True}

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
@app.get("/books/{book_id}/pdf")
async def get_book_pdf(
    book_id: int,
    db: Session = Depends(get_db)
):
    """Получить PDF файл книги (временно без проверки владельца)"""
    book = db.query(models.Book).filter(
        models.Book.id == book_id
    ).first()
    
    if not book or not book.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    from fastapi.responses import FileResponse
    import os
    
    if not os.path.exists(book.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(book.pdf_path, filename=f"book_{book_id}.pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)