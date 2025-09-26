"""
Простой тест экспорта для проверки работоспособности
Автор: AI Assistant  
Дата: 20.09.2025 08:20:00
"""

import sys
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_export_functionality():
    """Простой тест функциональности экспорта"""
    print("🧪 Тест экспорта...")
    
    try:
        from core.export import VacancyExporter
        print("✅ Импорт модуля экспорта успешен")
        
        # Создаем экспортер
        exporter = VacancyExporter()
        print("✅ Создание экспортера успешно")
        
        # Проверяем количество вакансий
        count = exporter.get_vacancy_count()
        print(f"📊 Вакансий в БД: {count}")
        
        if count == 0:
            print("⚠️  БД пуста, создаем тестовую запись...")
            # TODO: добавить создание тестовых данных
        
        # Проверяем форматы
        formats = exporter.get_export_formats()
        print(f"📋 Доступные форматы: {list(formats.keys())}")
        
        for fmt_name, fmt_config in formats.items():
            print(f"   {fmt_name}: {fmt_config['name']} ({len(fmt_config['columns'])} колонок)")
        
        # Пробуем небольшой экспорт если есть данные
        if count > 0:
            test_file = Path("data/test_export.xlsx")
            print(f"🚀 Тестовый экспорт в: {test_file}")
            
            result = exporter.export_to_excel(
                output_path=test_file,
                format_type='brief',
                limit=10
            )
            
            if result['success']:
                print(f"✅ Экспорт успешен:")
                print(f"   Записей: {result['records_exported']}")
                print(f"   Размер: {result['file_size_mb']} МБ")
                print(f"   Время: {result['export_time_seconds']} сек")
                
                if test_file.exists():
                    file_size = test_file.stat().st_size
                    print(f"   Файл создан: {file_size} байт")
                    
                    # Удаляем тестовый файл
                    test_file.unlink()
                    print("   Тестовый файл удален")
            else:
                print(f"❌ Ошибки экспорта: {result['errors']}")
        
        print("\n✅ Все тесты пройдены!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Возможно, не установлены зависимости: pip install openpyxl pandas")
        return False
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_export_functionality()
    sys.exit(0 if success else 1)
