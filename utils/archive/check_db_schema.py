"""
Проверка реальной схемы БД для исправления экспортера
"""

import sqlite3
from pathlib import Path

def check_db_schema():
    """Проверка схемы БД v4"""
    db_path = "data/hh_v4.sqlite3"
    
    if not Path(db_path).exists():
        print(f"❌ БД не найдена: {db_path}")
        return
    
    print(f"🔍 Проверяем схему: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Получаем информацию о таблице vacancies
    cursor.execute("PRAGMA table_info(vacancies)")
    columns = cursor.fetchall()
    
    print(f"\n📋 Колонки таблицы 'vacancies' ({len(columns)} штук):")
    for i, col in enumerate(columns):
        col_id, name, type_name, not_null, default, pk = col
        print(f"  {i+1:2d}. {name:25} | {type_name:10} | NotNull: {not_null} | PK: {pk}")
    
    # Показываем несколько записей для понимания данных
    cursor.execute("SELECT COUNT(*) FROM vacancies")
    total_count = cursor.fetchone()[0]
    print(f"\n📊 Всего записей: {total_count}")
    
    if total_count > 0:
        # Первые 3 записи
        column_names = [col[1] for col in columns]
        cursor.execute(f"SELECT {', '.join(column_names[:10])} FROM vacancies LIMIT 3")
        rows = cursor.fetchall()
        
        print(f"\n📄 Первые 3 записи (первые 10 колонок):")
        for i, row in enumerate(rows, 1):
            print(f"  Запись {i}:")
            for j, (col_name, value) in enumerate(zip(column_names[:10], row)):
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"    {col_name:20}: {display_value}")
    
    conn.close()
    
    # Сохраняем результаты в файл
    with open("utils/db_schema_results.txt", "w", encoding="utf-8") as f:
        f.write(f"БД: {db_path}\n")
        f.write(f"Колонок: {len(columns)}\n")
        f.write(f"Записей: {total_count}\n\n")
        f.write("КОЛОНКИ:\n")
        for i, col in enumerate(columns):
            col_id, name, type_name, not_null, default, pk = col
            f.write(f"{i+1:2d}. {name:25} | {type_name:10} | NotNull: {not_null} | PK: {pk}\n")
    
    print(f"\n✅ Результаты сохранены в: utils/db_schema_results.txt")

if __name__ == "__main__":
    check_db_schema()
