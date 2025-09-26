"""
Прямой тест экспорта без лишних зависимостей
"""

import sqlite3
import pandas as pd
from pathlib import Path

def direct_test():
    # Прямой SQL запрос к БД
    conn = sqlite3.connect("data/hh_v4.sqlite3")
    
    # Простой запрос 10 записей
    query = """
    SELECT title, company, salary_from, salary_to, currency, 
           experience, area, published_at, url, filter_id 
    FROM vacancies 
    ORDER BY created_at DESC 
    LIMIT 10
    """
    
    # Выполняем запрос
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"📊 Получено записей: {len(df)}")
    print(f"📋 Колонки: {list(df.columns)}")
    
    if len(df) > 0:
        print("\n📄 Первые 3 записи:")
        for i, row in df.head(3).iterrows():
            print(f"  {i+1}. {row['title'][:40]}... | {row['company']} | {row['area']}")
    
    # Экспорт в Excel
    output_file = Path("data/direct_test_export.xlsx")
    print(f"\n📁 Экспорт в: {output_file}")
    
    try:
        df.to_excel(output_file, index=False)
        
        if output_file.exists():
            size = output_file.stat().st_size
            print(f"✅ Файл создан: {size} байт")
            
            # Сохраняем результат в текстовый файл
            with open("utils/direct_export_result.txt", "w", encoding="utf-8") as f:
                f.write(f"Прямой экспорт результат:\n")
                f.write(f"Записей: {len(df)}\n")
                f.write(f"Размер файла: {size} байт\n")
                f.write(f"Путь: {output_file}\n")
                f.write(f"Колонки: {', '.join(df.columns)}\n")
            
            return True
        else:
            print("❌ Файл не создан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")
        return False

if __name__ == "__main__":
    direct_test()
