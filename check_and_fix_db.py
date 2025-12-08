"""
Скрипт для проверки и исправления структуры базы данных.
Добавляет отсутствующие столбцы в существующие таблицы.
"""
from database import engine
from sqlalchemy import text

def check_and_fix_database():
    print("🔍 Проверка структуры базы данных...")
    
    with engine.connect() as conn:
        # Проверяем есть ли столбец pdf_path в таблице books
        try:
            result = conn.execute(text("SELECT pdf_path FROM books LIMIT 1"))
            print("✅ Столбец pdf_path существует в таблице books")
            return True
        except Exception as e:
            if "no such column" in str(e):
                print("❌ Столбец pdf_path отсутствует. Добавляем...")
                try:
                    # Добавляем столбец
                    conn.execute(text("ALTER TABLE books ADD COLUMN pdf_path VARCHAR"))
                    conn.commit()
                    print("✅ Столбец pdf_path успешно добавлен")
                    return True
                except Exception as alter_error:
                    print(f"❌ Ошибка при добавлении столбца: {alter_error}")
                    return False
            else:
                print(f"❌ Другая ошибка: {e}")
                return False

if __name__ == "__main__":
    success = check_and_fix_database()
    exit(0 if success else 1)
