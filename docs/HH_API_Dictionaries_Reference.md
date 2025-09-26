# Справочники API HH.ru - Документация для HH-бота v4

*Создано: 19.09.2025 21:10:00*

## 📚 Основные справочники HH.ru API

### Общая информация
Все справочники доступны через единый endpoint или индивидуально:
- **Все сразу**: `GET https://api.hh.ru/dictionaries`
- **Отдельные**: `GET https://api.hh.ru/{dictionary_name}`

### Кэширование и обновление
- **Частота обновления**: раз в неделю (воскресенье 03:00)
- **Кэширование**: локально в БД таблица `hh_dictionaries`
- **Срок актуальности**: 7 дней

## 🗂️ Справочники для поиска вакансий

### 1. areas - Регионы и города
**Endpoint**: `GET https://api.hh.ru/areas`
**Использование**: Фильтрация по местоположению

```json
{
  "id": "1",
  "name": "Москва", 
  "areas": [
    {
      "id": "1",
      "name": "Москва"
    }
  ]
}
```

**Применение в фильтрах**:
```json
{
  "area": 1,           // Москва
  "area": 2,           // Санкт-Петербург  
  "area": 113,         // Россия (все города)
  "area": [1, 2]       // Несколько городов
}
```

**Важные коды регионов**:
- `1` - Москва
- `2` - Санкт-Петербург  
- `3` - Екатеринбург
- `4` - Новосибирск
- `113` - Россия (все города)

### 2. metro - Станции метро
**Endpoint**: `GET https://api.hh.ru/metro`
**Использование**: Точная геопривязка в крупных городах

```json
{
  "id": "1.1",
  "name": "Сокольническая",
  "lines": [
    {
      "id": "1.1", 
      "name": "Сокольническая",
      "stations": [
        {
          "id": "1.1",
          "name": "Сокольники"
        }
      ]
    }
  ]
}
```

### 3. specializations - Профессиональные области
**Endpoint**: `GET https://api.hh.ru/specializations`
**Использование**: Категоризация по отраслям

```json
{
  "id": "1",
  "name": "Информационные технологии, интернет, телеком",
  "specializations": [
    {
      "id": "1.221",
      "name": "Программирование, Разработка",
      "laboring": false
    }
  ]
}
```

**IT специализации**:
- `1.221` - Программирование, Разработка
- `1.164` - Системное администрирование  
- `1.113` - Интернет, мультимедиа технологии
- `1.89` - Тестирование

### 4. experience - Уровни опыта
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел experience)

```json
[
  {
    "id": "noExperience",
    "name": "Нет опыта"
  },
  {
    "id": "between1And3", 
    "name": "От 1 года до 3 лет"
  },
  {
    "id": "between3And6",
    "name": "От 3 до 6 лет"
  },
  {
    "id": "moreThan6",
    "name": "Более 6 лет"
  }
]
```

### 5. employment - Тип занятости
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел employment)

```json
[
  {
    "id": "full",
    "name": "Полная занятость"
  },
  {
    "id": "part", 
    "name": "Частичная занятость"
  },
  {
    "id": "project",
    "name": "Проектная работа"
  },
  {
    "id": "volunteer",
    "name": "Волонтерство"
  },
  {
    "id": "probation",
    "name": "Стажировка"
  }
]
```

### 6. schedule - График работы
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел schedule)

```json
[
  {
    "id": "fullDay",
    "name": "Полный день"
  },
  {
    "id": "shift",
    "name": "Сменный график"
  },
  {
    "id": "flexible", 
    "name": "Гибкий график"
  },
  {
    "id": "remote",
    "name": "Удаленная работа"
  },
  {
    "id": "flyInFlyOut",
    "name": "Вахтовый метод"
  }
]
```

## 💰 Справочники для зарплат

### 7. currencies - Валюты
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел currency)

```json
[
  {
    "abbr": "RUR",
    "code": "RUR", 
    "name": "руб."
  },
  {
    "abbr": "USD",
    "code": "USD",
    "name": "USD"
  },
  {
    "abbr": "EUR", 
    "code": "EUR",
    "name": "EUR"
  }
]
```

### 8. vacancy_billing_type - Тип размещения вакансии
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел vacancy_billing_type)

```json
[
  {
    "id": "free",
    "name": "Бесплатная"
  },
  {
    "id": "standard", 
    "name": "Стандарт"
  },
  {
    "id": "standard_plus",
    "name": "Стандарт плюс"
  },
  {
    "id": "premium",
    "name": "Премиум"
  }
]
```

## 🔍 Справочники для поисковых параметров

### 9. vacancy_search_fields - Поля для поиска
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел vacancy_search_fields)

```json
[
  {
    "id": "name",
    "name": "в названии вакансии"
  },
  {
    "id": "company_name", 
    "name": "в названии компании"
  },
  {
    "id": "description",
    "name": "в описании вакансии"
  }
]
```

### 10. vacancy_search_order - Сортировка результатов
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел vacancy_search_order)

```json
[
  {
    "id": "relevance",
    "name": "по соответствию"
  },
  {
    "id": "publication_time",
    "name": "по дате"
  },
  {
    "id": "salary_desc", 
    "name": "по убыванию зарплаты"
  },
  {
    "id": "salary_asc",
    "name": "по возрастанию зарплаты"
  }
]
```

## 🏢 Справочники для работодателей

### 11. employer_type - Тип работодателя
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел employer_type)

```json
[
  {
    "id": "company",
    "name": "Компания"
  },
  {
    "id": "agency",
    "name": "Кадровое агентство"
  },
  {
    "id": "private_recruiter", 
    "name": "Частный рекрутер"
  }
]
```

### 12. industries - Отрасли
**Endpoint**: `GET https://api.hh.ru/industries`

```json
[
  {
    "id": "7",
    "name": "Информационные технологии, системная интеграция, интернет",
    "industries": [
      {
        "id": "7.513",
        "name": "Интернет-провайдер"
      }
    ]
  }
]
```

## 🗃️ Дополнительные справочники

### 13. languages - Языки
**Endpoint**: `GET https://api.hh.ru/languages`

```json
[
  {
    "id": "en",
    "name": "Английский"
  },
  {
    "id": "de",
    "name": "Немецкий"  
  },
  {
    "id": "fr",
    "name": "Французский"
  }
]
```

### 14. driver_license_types - Типы водительских прав
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел driver_license_types)

```json
[
  {
    "id": "A",
    "name": "A"
  },
  {
    "id": "B", 
    "name": "B"
  },
  {
    "id": "C",
    "name": "C"
  }
]
```

### 15. employment_form - Форма трудоустройства
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел employment_form)

```json
[
  {
    "id": "FULL",
    "name": "Полная"
  },
  {
    "id": "PART",
    "name": "Частичная"
  },
  {
    "id": "PROJECT",
    "name": "Проект или разовое задание"
  },
  {
    "id": "FLY_IN_FLY_OUT",
    "name": "Вахта"
  }
]
```

### 16. work_format - Формат работы
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел work_format)

```json
[
  {
    "id": "ON_SITE",
    "name": "На месте работодателя"
  },
  {
    "id": "REMOTE",
    "name": "Удалённо"
  },
  {
    "id": "HYBRID",
    "name": "Гибрид"
  },
  {
    "id": "FIELD_WORK",
    "name": "Разъездной"
  }
]
```

### 17. working_hours - Количество рабочих часов
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел working_hours)

```json
[
  {
    "id": "HOURS_2",
    "name": "2 часа"
  },
  {
    "id": "HOURS_4",
    "name": "4 часа"
  },
  {
    "id": "HOURS_8",
    "name": "8 часов"
  },
  {
    "id": "HOURS_12",
    "name": "12 часов"
  },
  {
    "id": "FLEXIBLE",
    "name": "По договорённости"
  }
]
```

### 18. work_schedule_by_days - График работы по дням
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел work_schedule_by_days)

```json
[
  {
    "id": "FIVE_ON_TWO_OFF",
    "name": "5/2"
  },
  {
    "id": "TWO_ON_TWO_OFF",
    "name": "2/2"
  },
  {
    "id": "FLEXIBLE",
    "name": "Свободный"
  },
  {
    "id": "WEEKEND",
    "name": "По выходным"
  }
]
```

### 19. salary_range_mode - Режим оплаты
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел salary_range_mode)

```json
[
  {
    "id": "MONTH",
    "name": "За месяц"
  },
  {
    "id": "SHIFT",
    "name": "За смену"
  },
  {
    "id": "HOUR",
    "name": "За час"
  },
  {
    "id": "FLY_IN_FLY_OUT",
    "name": "За вахту"
  }
]
```

### 20. age_restriction - Возрастные ограничения
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел age_restriction)

```json
[
  {
    "id": "AGE_14_PLUS",
    "name": "От 14 лет"
  },
  {
    "id": "AGE_16_PLUS",
    "name": "От 16 лет"
  }
]
```

### 21. language_level - Уровни знания языков
**Endpoint**: `GET https://api.hh.ru/dictionaries` (раздел language_level)

```json
[
  {
    "id": "a1",
    "name": "A1 — Начальный"
  },
  {
    "id": "b1",
    "name": "B1 — Средний"
  },
  {
    "id": "c1",
    "name": "C1 — Продвинутый"
  },
  {
    "id": "l1",
    "name": "Родной"
  }
]
```

### 22. key_skills - Ключевые навыки
**Получение**: Через поиск вакансий, не отдельный справочник
**Пример значений**: "Python", "JavaScript", "SQL", "Docker", "Kubernetes"

## 💾 Реализация в HH-боте v4

### Структура хранения в БД

```sql
-- Таблица для кэширования справочников
CREATE TABLE hh_dictionaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dictionary_name TEXT NOT NULL,        -- 'areas', 'experience', etc.
    item_id TEXT NOT NULL,               -- ID элемента из HH
    item_name TEXT NOT NULL,             -- Название элемента
    parent_id TEXT,                      -- Для иерархических справочников
    metadata TEXT,                       -- JSON с дополнительными данными
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    UNIQUE(dictionary_name, item_id)
);

-- Индексы для быстрого поиска
CREATE INDEX idx_dict_name_id ON hh_dictionaries(dictionary_name, item_id);
CREATE INDEX idx_dict_expires ON hh_dictionaries(expires_at);
```

### Класс для работы со справочниками

```python
class HHDictionaryManager:
    """Менеджер для работы со справочниками HH.ru"""
    
    def __init__(self, database: VacancyDatabase, fetcher: VacancyFetcher):
        self.database = database
        self.fetcher = fetcher
        self.cache_duration = timedelta(days=7)
    
    def get_areas(self, refresh: bool = False) -> List[Dict]:
        """Получить список регионов"""
        return self._get_dictionary('areas', refresh)
    
    def get_experience_levels(self, refresh: bool = False) -> List[Dict]:
        """Получить уровни опыта"""
        return self._get_dictionary('experience', refresh)
    
    def get_employment_types(self, refresh: bool = False) -> List[Dict]:
        """Получить типы занятости"""
        return self._get_dictionary('employment', refresh)
    
    def refresh_all_dictionaries(self) -> Dict[str, int]:
        """Обновить все справочники"""
        results = {}
        dictionaries = [
            'areas', 'metro', 'specializations', 'experience',
            'employment', 'schedule', 'currencies', 'industries',
            'vacancy_billing_type', 'employment_form', 'work_format',
            'working_hours', 'work_schedule_by_days', 'salary_range_mode',
            'age_restriction', 'language_level'
        ]
        
        for dict_name in dictionaries:
            try:
                count = self._refresh_dictionary(dict_name)
                results[dict_name] = count
            except Exception as e:
                logger.error(f"Failed to refresh {dict_name}: {e}")
                results[dict_name] = -1
        
        return results
    
    def _get_dictionary(self, name: str, refresh: bool = False) -> List[Dict]:
        """Получить справочник с кэшированием"""
        if refresh or self._is_cache_expired(name):
            self._refresh_dictionary(name)
        
        return self._load_from_cache(name)
    
    def _is_cache_expired(self, name: str) -> bool:
        """Проверить актуальность кэша"""
        result = self.database.execute_sql(
            "SELECT MAX(expires_at) FROM hh_dictionaries WHERE dictionary_name = ?",
            (name,)
        )
        
        if not result or not result[0][0]:
            return True
        
        expires_at = datetime.fromisoformat(result[0][0])
        return datetime.now() > expires_at
    
    def _refresh_dictionary(self, name: str) -> int:
        """Обновить справочник из API"""
        if name == 'areas':
            url = "https://api.hh.ru/areas"
        elif name in ['experience', 'employment', 'schedule', 'currencies']:
            url = "https://api.hh.ru/dictionaries"
        else:
            url = f"https://api.hh.ru/{name}"
        
        response = self.fetcher._make_request(url)
        data = response.json()
        
        # Очистить старые данные
        self.database.execute_sql(
            "DELETE FROM hh_dictionaries WHERE dictionary_name = ?",
            (name,)
        )
        
        # Сохранить новые данные
        count = self._save_dictionary_data(name, data)
        
        logger.info(f"Refreshed {name} dictionary: {count} items")
        return count
```

### Интеграция с фильтрами

```python
# В config/filters.json можно использовать понятные названия
{
  "search_profiles": [
    {
      "name": "Python Middle Moscow",
      "text": "python разработчик middle",
      "area": "Москва",              # Будет конвертировано в area: 1
      "experience": "От 1 года до 3 лет",  # Будет конвертировано в experience: "between1And3"
      "employment": "Полная занятость",     # Будет конвертировано в employment: "full"
      "schedule": "Удаленная работа",       # Будет конвертировано в schedule: "remote"
      "enabled": true
    }
  ]
}
```

### CLI команды для справочников

```python
# В cli_v4.py
@cli.command()
@click.option('--dictionary', help='Конкретный справочник для обновления')  
@click.option('--force', is_flag=True, help='Принудительное обновление')
def update_dictionaries(dictionary: str, force: bool):
    """Обновить справочники HH.ru"""
    
    dict_manager = HHDictionaryManager(database, fetcher)
    
    if dictionary:
        count = dict_manager._refresh_dictionary(dictionary)
        print(f"Обновлен справочник '{dictionary}': {count} элементов")
    else:
        results = dict_manager.refresh_all_dictionaries()
        for name, count in results.items():
            if count >= 0:
                print(f"✅ {name}: {count} элементов")
            else:
                print(f"❌ {name}: ошибка обновления")

@cli.command()
@click.argument('dictionary_name')
@click.option('--search', help='Поиск по названию')
def show_dictionary(dictionary_name: str, search: str):
    """Показать содержимое справочника"""
    
    dict_manager = HHDictionaryManager(database, fetcher)
    items = dict_manager._get_dictionary(dictionary_name)
    
    if search:
        items = [item for item in items if search.lower() in item['name'].lower()]
    
    for item in items[:20]:  # Показать первые 20
        print(f"{item['id']}: {item['name']}")
    
    if len(items) > 20:
        print(f"... и еще {len(items) - 20} элементов")
```

## 🔄 Автоматическое обновление

### Планировщик обновлений

```python
class DictionaryUpdateScheduler:
    """Планировщик автоматического обновления справочников"""
    
    def schedule_weekly_update(self):
        """Запланировать еженедельное обновление"""
        # Каждое воскресенье в 03:00
        schedule.every().sunday.at("03:00").do(self.update_all_dictionaries)
    
    def update_all_dictionaries(self):
        """Обновить все справочники"""
        try:
            dict_manager = HHDictionaryManager(database, fetcher)
            results = dict_manager.refresh_all_dictionaries()
            
            # Отправить уведомление о результатах
            if telegram_notifier:
                message = self._format_update_report(results)
                telegram_notifier.send_message(message, priority="info")
                
        except Exception as e:
            logger.error(f"Dictionary update failed: {e}")
            if telegram_notifier:
                telegram_notifier.send_message(
                    f"❌ Ошибка обновления справочников: {e}",
                    priority="error"
                )
```

## 📋 Практические примеры использования

### Валидация фильтров
```python
def validate_search_filters(filters: Dict) -> Dict:
    """Валидация и конвертация фильтров поиска"""
    dict_manager = HHDictionaryManager(database, fetcher)
    
    validated = {}
    
    # Валидация региона
    if 'area' in filters:
        areas = dict_manager.get_areas()
        area_map = {item['name']: item['id'] for item in areas}
        
        if isinstance(filters['area'], str):
            if filters['area'] in area_map:
                validated['area'] = int(area_map[filters['area']])
            else:
                raise ValueError(f"Неизвестный регион: {filters['area']}")
        else:
            validated['area'] = filters['area']
    
    # Валидация опыта
    if 'experience' in filters:
        experience_levels = dict_manager.get_experience_levels()
        exp_map = {item['name']: item['id'] for item in experience_levels}
        
        if isinstance(filters['experience'], str):
            if filters['experience'] in exp_map:
                validated['experience'] = exp_map[filters['experience']]
            else:
                raise ValueError(f"Неизвестный уровень опыта: {filters['experience']}")
        else:
            validated['experience'] = filters['experience']
    
    return validated
```

### Пользовательский интерфейс
```python
def show_available_filters():
    """Показать доступные фильтры для пользователя"""
    dict_manager = HHDictionaryManager(database, fetcher)
    
    print("🌍 Доступные регионы:")
    areas = dict_manager.get_areas()
    for area in areas[:10]:  # Топ-10 регионов
        print(f"  {area['name']}")
    
    print("\n💼 Уровни опыта:")
    experience = dict_manager.get_experience_levels()
    for exp in experience:
        print(f"  {exp['name']}")
    
    print("\n📅 Графики работы:")
    schedules = dict_manager.get_schedule_types()
    for schedule in schedules:
        print(f"  {schedule['name']}")
```

*Обновлено: 19.09.2025 21:10:00*
