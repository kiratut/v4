"""
Реальный тест экспорта с исправленной схемой БД
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.export import VacancyExporter

def main():
    print("🚀 РЕАЛЬНЫЙ ТЕСТ ЭКСПОРТА")
    
    # Тестируем экспортер
    exporter = VacancyExporter("data/hh_v4.sqlite3")
    
    # Проверяем количество записей
    count = exporter.get_vacancy_count()
    print(f"📊 Записей в БД: {count}")
    
    if count == 0:
        print("❌ Нет данных для экспорта")
        return False
    
    # Экспортируем 100 записей для теста
    test_file = Path("data/test_export_real.xlsx")
    print(f"📁 Экспорт в: {test_file}")
    
    result = exporter.export_to_excel(
        output_path=test_file,
        format_type='brief',
        limit=100
    )
    
    print(f"✅ Результат экспорта:")
    print(f"   Успех: {result['success']}")
    print(f"   Записей: {result.get('records_exported', 0)}")
    print(f"   Размер: {result.get('file_size_mb', 0)} МБ")
    print(f"   Время: {result.get('export_time_seconds', 0)} сек")
    
    if result.get('errors'):
        print(f"   Ошибки: {result['errors']}")
    
    # Проверяем файл
    if test_file.exists():
        file_size = test_file.stat().st_size
        print(f"   Файл создан: {file_size} байт")
        
        # Записываем результаты
        with open("utils/export_test_results.txt", "w", encoding="utf-8") as f:
            f.write(f"Результат экспорта:\n")
            f.write(f"Успех: {result['success']}\n")
            f.write(f"Записей: {result.get('records_exported', 0)}\n")
            f.write(f"Размер: {result.get('file_size_mb', 0)} МБ\n")
            f.write(f"Размер файла: {file_size} байт\n")
            f.write(f"Файл: {test_file}\n")
        
        print("📄 Результаты сохранены в: utils/export_test_results.txt")
        return True
    else:
        print("❌ Файл не создан")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
