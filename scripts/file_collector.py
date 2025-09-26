#!/usr/bin/env python3
"""
File Collector - объединяет текстовые файлы в одну простыню

Собирает текстовые файлы из каталога и всех подкаталогов,
фильтруя по расширениям и размеру файлов.

Формат вывода:
1. Дерево каталога с символами + (включен) / - (исключен)
2. Статистика: сколько файлов включено/исключено
3. Содержимое файлов: путь + текст файла
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple


# === КОНФИГУРАЦИЯ ===
# Измените эти параметры по умолчанию

# Каталог для обработки
#DEFAULT_DIRECTORY = "."
DEFAULT_DIRECTORY = r"C:\DEV\hh-applicant-tool\hh_v3\v4\orchestrator\workspaces\REPAIR-2-8-4-001"

# Расширения файлов для включения (пустой список = все файлы)
DEFAULT_INCLUDE_EXTENSIONS = ["py", "md", "txt","json"]

# Расширения файлов для исключения
DEFAULT_EXCLUDE_EXTENSIONS = ["log", "bak", "pyc"]

# Максимальный размер файла в байтах (1MB = 1048576)
DEFAULT_MAX_SIZE = 100 * 1024

# Директории для исключения из обхода
DEFAULT_EXCLUDE_DIRS = ["backup", "examples", ".git", "logs", "__pycache__",".venv","node_modules"]

# Выходной файл (пустая строка = вывод в консоль)
# DEFAULT_OUTPUT_FILE = "docs/catalog_v4.md"
DEFAULT_OUTPUT_FILE = "docs/catalog_REPAIR-2-8-4-001.md"

# === КОНЕЦ КОНФИГУРАЦИИ ===


class FileCollector:
    def __init__(self, root_dir: str, include_ext: List[str], exclude_ext: List[str],
                 max_size: int, exclude_dirs: List[str], output_file: str = ""):
        self.root_dir = Path(root_dir).resolve()
        self.include_ext = set(ext.lower().lstrip('.') for ext in include_ext)
        self.exclude_ext = set(ext.lower().lstrip('.') for ext in exclude_ext)
        self.max_size = max_size
        self.exclude_dirs = set(exclude_dirs)
        self.output_file = output_file
        
        self.included_files = []
        self.excluded_files = []
        self.tree_lines = []
        self.output_lines = []
        
        # Статистика
        self.included_dirs = set()
        self.excluded_dirs = set()
        self.total_lines = 0
        self.total_size = 0
        self.cumulative_line = 1  # номер следующей строки в итоговом файле
        self.file_line_info = {}  # mapping Path -> (start_line, line_count)
        self.file_contents = {}  # cache file contents

    def write_output(self, text: str, end: str = "\n", to_console: bool = False):
        """Записать текст в вывод (файл всегда, консоль по выбору)"""
        # Всегда в файл
        if self.output_file:
            self.output_lines.append(text + end)
        
        # В консоль только если указано
        if to_console:
            print(text, end=end)

    def save_output(self):
        """Сохранить накопленный вывод в файл"""
        if self.output_file and self.output_lines:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(self.output_lines)
            
            print(f"\n✅ Результаты сохранены в: {self.output_file}")

    def count_lines(self, text: str) -> int:
        """Подсчитать количество строк в тексте"""
        return len(text.splitlines())

    def should_include_file(self, file_path: Path) -> bool:
        """Проверяет, нужно ли включить файл в сборку"""
        # Проверяем размер
        if file_path.stat().st_size > self.max_size:
            return False

        # Получаем расширение без точки
        ext = file_path.suffix.lower().lstrip('.')

        # Если указаны расширения для включения - проверяем их
        if self.include_ext:
            if ext not in self.include_ext:
                return False

        # Проверяем расширения для исключения
        if ext in self.exclude_ext:
            return False

        return True

    def should_exclude_dir(self, dir_path: Path) -> bool:
        """Проверяет, нужно ли исключить директорию из обхода"""
        dir_name = dir_path.name
        return dir_name in self.exclude_dirs or dir_name.startswith('.')

    def build_tree(self, current_path: Path = None, prefix: str = "", is_last: bool = True) -> None:
        """Строит дерево каталога с символами включения/исключения и номерами строк"""
        if current_path is None:
            current_path = self.root_dir
            self.tree_lines.append(f"{current_path}")

        try:
            items = sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return

        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "└── " if is_last_item else "├── "

            # Определяем символ включения
            if item.is_file():
                included = self.should_include_file(item)
                symbol = "+" if included else "-"
                
                # Добавляем в списки и статистику
                if included:
                    self.included_files.append(item)
                    self.total_size += item.stat().st_size
                    
                    # Читаем и кэшируем содержимое
                    content = self.read_file_content(item)
                    self.file_contents[item] = content
                    line_count = self.count_lines(content)
                    self.file_line_info[item] = (self.cumulative_line, line_count)
                    self.cumulative_line += line_count + 3  # +3 для разделителей
                    
                    # Добавляем директорию файла в включенные
                    parent_dir = item.parent
                    if parent_dir != self.root_dir:
                        self.included_dirs.add(str(parent_dir.relative_to(self.root_dir)))
                    
                    # Форматируем строку с информацией о строках
                    line_info = f"{self.file_line_info[item][0]}, {line_count}"
                    line = f"{prefix}{connector}{symbol} {item.name}  {line_info}"
                else:
                    self.excluded_files.append(item)
                    line = f"{prefix}{connector}{symbol} {item.name}"
                    
            else:  # директория
                included = not self.should_exclude_dir(item)
                symbol = "+" if included else "-"
                
                # Добавляем в статистику директорий
                if item != self.root_dir:
                    rel_path = str(item.relative_to(self.root_dir))
                    if included:
                        self.included_dirs.add(rel_path)
                    else:
                        self.excluded_dirs.add(rel_path)

                line = f"{prefix}{connector}{symbol} {item.name}/"

            # Добавляем в дерево
            self.tree_lines.append(line)

            # Рекурсивно обрабатываем поддиректории
            if item.is_dir() and not self.should_exclude_dir(item):
                extension = "    " if is_last_item else "│   "
                self.build_tree(item, prefix + extension, is_last_item)

    def read_file_content(self, file_path: Path) -> str:
        """Читает содержимое файла с поддержкой UTF-8 и CP1251"""
        try:
            # Сначала пробуем UTF-8
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Пробуем CP1251 (Windows-1251) для русских файлов
                try:
                    with open(file_path, 'r', encoding='cp1251') as f:
                        return f.read()
                except UnicodeDecodeError:
                    # Пробуем Latin-1 как последний вариант
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            return f.read()
                    except:
                        # Если ничего не помогло, используем utf-8 с заменой ошибок
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            return f.read()

        except Exception as e:
            return f"Ошибка чтения файла: {e}"

    def collect_files(self) -> None:
        """Основной метод сбора файлов"""
        # Выводим начальную информацию в файл
        self.write_output(f"🔍 Сбор файлов из: {self.root_dir}")
        self.write_output(f"📁 Включить расширения: {', '.join(self.include_ext) if self.include_ext else 'все'}")
        self.write_output(f"🚫 Исключить расширения: {', '.join(self.exclude_ext) if self.exclude_ext else 'нет'}")
        self.write_output(f"📏 Максимальный размер: {self.max_size:,} байт")
        self.write_output(f"🚷 Исключить папки: {', '.join(self.exclude_dirs) if self.exclude_dirs else 'нет'}")
        self.write_output("")

        # Строим дерево и собираем файлы
        self.build_tree()

        # Выводим статистику в файл
        self.write_output("📊 СТАТИСТИКА:")
        self.write_output(f"✅ Включено файлов: {len(self.included_files)}")
        self.write_output(f"❌ Исключено файлов: {len(self.excluded_files)}")
        self.write_output(f"📁 Включено директорий: {len(self.included_dirs)}")
        self.write_output(f"🚷 Исключено директорий: {len(self.excluded_dirs)}")
        self.write_output(f"📏 Общий размер файлов: {self.total_size:,} байт")
        self.write_output("")

        # Выводим дерево в файл
        self.write_output("📂 СТРУКТУРА КАТАЛОГА:")
        for line in self.tree_lines:
            self.write_output(line)
        self.write_output("\n" + "="*80 + "\n")

        # Выводим содержимое файлов в файл
        self.write_output("📄 СОДЕРЖИМОЕ ФАЙЛОВ:")
        self.write_output("="*80)

        for i, file_path in enumerate(self.included_files, 1):
            relative_path = file_path.relative_to(self.root_dir)
            file_size = file_path.stat().st_size
            
            # Получаем информацию о строках из кэша
            start_line, line_count = self.file_line_info[file_path]
            content = self.file_contents[file_path]

            self.write_output(f"\n{'='*40} ФАЙЛ {i}/{len(self.included_files)} {'='*40}")
            self.write_output(f"📁 Путь: {relative_path}")
            self.write_output(f"📏 Размер: {file_size:,} байт")
            self.write_output(f"🔤 Тип: {file_path.suffix}")
            self.write_output(f"📍 Начало строки: {start_line}")
            self.write_output(f"📊 Количество строк: {line_count}")
            self.write_output("-" * 80)

            self.write_output(content)
            
            # Добавляем в статистику строк
            self.total_lines += line_count
            
            self.write_output("\n" + "="*80)

        # Выводим итоговую статистику в консоль
        print("\n" + "="*60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"✅ Включено файлов: {len(self.included_files)}")
        print(f"❌ Исключено файлов: {len(self.excluded_files)}")
        print(f"📁 Включено директорий: {len(self.included_dirs)}")
        print(f"🚷 Исключено директорий: {len(self.excluded_dirs)}")
        print(f"📏 Общий размер файлов: {self.total_size:,} байт")
        print(f"📝 Общее количество строк: {self.total_lines:,}")
        print("="*60)

        # Сохраняем в файл если указан
        self.save_output()


def main():
    parser = argparse.ArgumentParser(
        description="File Collector - объединяет текстовые файлы в одну простыню",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python file_collector.py . --include txt,py,md --exclude log,bak --max-size 1048576
  python file_collector.py /path/to/project --include py --exclude pyc --exclude-dirs .git,__pycache__,node_modules
  python file_collector.py docs/ --include md,txt --max-size 524288
  python file_collector.py . --output docs/catalog.md --include py,md,txt

Параметры по умолчанию можно изменить в начале файла в секции КОНФИГУРАЦИЯ
        """
    )

    parser.add_argument('directory', nargs='?', default=DEFAULT_DIRECTORY,
                       help='Каталог для обработки')
    parser.add_argument('--include', nargs='+', default=DEFAULT_INCLUDE_EXTENSIONS,
                       help='Расширения файлов для включения (без точки)')
    parser.add_argument('--exclude', nargs='+', default=DEFAULT_EXCLUDE_EXTENSIONS,
                       help='Расширения файлов для исключения (без точки)')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE,
                       help='Максимальный размер файла в байтах (по умолчанию 1MB)')
    parser.add_argument('--exclude-dirs', nargs='+', default=DEFAULT_EXCLUDE_DIRS,
                       help='Имена папок для исключения из обхода')
    parser.add_argument('--output', default=DEFAULT_OUTPUT_FILE,
                       help='Файл для сохранения результатов (по умолчанию вывод в консоль)')

    args = parser.parse_args()

    # Проверяем существование каталога
    if not os.path.exists(args.directory):
        print(f"❌ Каталог не существует: {args.directory}")
        sys.exit(1)

    if not os.path.isdir(args.directory):
        print(f"❌ Указанный путь не является каталогом: {args.directory}")
        sys.exit(1)

    # Создаем сборщик и запускаем
    collector = FileCollector(
        root_dir=args.directory,
        include_ext=args.include,
        exclude_ext=args.exclude,
        max_size=args.max_size,
        exclude_dirs=args.exclude_dirs,
        output_file=args.output
    )

    try:
        collector.collect_files()
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
