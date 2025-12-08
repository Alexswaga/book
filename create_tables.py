"""
Скрипт для создания/обновления таблиц базы данных.
"""
from database import engine
import models
import sys

def init_database():
    """Создать все таблицы если их нет"""
    print("🔄 Создание/обновление таблиц базы данных...")
    
    try:
        # Создаем все таблицы
        models.Base.metadata.create_all(bind=engine)
        print("✅ Таблицы созданы/проверены")
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
