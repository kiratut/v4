"""
ПРЯМАЯ ПРОВЕРКА РЕАЛЬНЫХ ДАННЫХ без терминальных команд
Этот файл будет создан и результат можно прочитать через Read tool

Автор: AI Assistant
Дата: 20.09.2025 09:35:00
"""

import sys
import sqlite3
from pathlib import Path

def check_databases():
    """Проверка всех БД файлов"""
    results = []
    results.append("=== ПРОВЕРКА РЕАЛЬНЫХ ДАННЫХ ===")
    results.append(f"Время проверки: 2025-09-20 09:35:00")
    
    # Проверяем все sqlite файлы в data/
    data_dir = Path("data")
    if not data_dir.exists():
        results.append("❌ Папка data/ не существует!")
        return results
    
    db_files = list(data_dir.glob("*.sqlite3"))
    results.append(f"\n📁 Найдено БД файлов: {len(db_files)}")
    
    for db_file in db_files:
        results.append(f"\n🗄️  БД: {db_file.name}")
        results.append(f"   Размер: {db_file.stat().st_size} байт ({db_file.stat().st_size / 1024 / 1024:.2f} МБ)")
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Проверяем таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            results.append(f"   Таблиц: {len(tables)}")
            
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    results.append(f"   - {table_name}: {count} записей")
                    
                    if table_name == 'vacancies' and count > 0:
                        # Показываем последние записи
                        cursor.execute(f"SELECT title, employer_name, created_at FROM {table_name} ORDER BY created_at DESC LIMIT 3")
                        recent = cursor.fetchall()
                        results.append(f"     Последние записи:")
                        for r in recent:
                            results.append(f"     • {r[0][:30]}... | {r[1]} | {r[2]}")
                            
                except Exception as e:
                    results.append(f"   - {table_name}: ошибка подсчета - {e}")
            
            conn.close()
            
        except Exception as e:
            results.append(f"   ❌ Ошибка подключения: {e}")
    
    return results

def main():
    """Основная функция"""
    results = check_databases()
    
    # Записываем результаты в файл
    output_file = Path("utils/database_check_results.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in results:
            f.write(line + "\n")
            
    # Также выводим в консоль
    for line in results:
        print(line)
        
    print(f"\n✅ Результаты сохранены в: {output_file}")

if __name__ == "__main__":
    main()
