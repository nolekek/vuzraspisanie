# Автономный микросервис составления расписания кафедры на Timefold Solver

Высокопроизводительный оптимизационный микросервис («черный ящик») для автоматического составления расписания университетской кафедры на базе **Timefold Solver**, **FastAPI**, **Pydantic v2** и **Python 3.12** с интерактивным веб-интерфейсом (UI Workbench) и парсером реального расписания УрГПУ (uspu.ru).

## 1. Архитектура и стек
- **Optimization Engine:** Timefold Solver 1.24+ (JPype + OpenJDK 17)
- **API Framework:** FastAPI + Pydantic v2 + Uvicorn
- **Frontend / UI Workbench:** HTML5 / Tailwind CSS / Vanilla JS (SPA на `/` и `/ui`)
- **Data Parser:** Парсер реального расписания с `https://uspu.ru/education/eios/schedule/`
- **Testing:** pytest + Timefold ConstraintVerifier + Reverse Generation Tests
- **Containerization:** Docker (Python 3.12 + Headless JRE 17)

## 2. Структура проекта
```
D:\4vuzraspisanie\
├── Dockerfile                         # Сборка контейнера с Python 3.12 и JRE
├── docker-compose.yml                 # Деплой микросервиса
├── requirements.txt                   # Зависимости
├── data/
│   └── uspu_schedule.json             # Спарсенный живой датасет расписания УрГПУ (47 занятий)
├── app/
│   ├── main.py                        # Входная точка FastAPI, раздача UI на / и /ui
│   ├── static/
│   │   └── index.html                 # Интерактивный UI Workbench (сетка расписания, метрики, аудит)
│   ├── domain/
│   │   ├── enums.py                   # DayOfWeek, WeekFrequency, TargetType, overlaps_week
│   │   ├── models.py                  # BaseSlot, Room, Teacher, AtomicGroup, ExternalBlock
│   │   └── solution.py                # Lesson (@planning_entity), TimetableSolution (@planning_solution)
│   ├── solver/
│   │   ├── constraints.py             # 13 Hard и Soft правил ConstraintProvider
│   │   └── service.py                 # SolverService (асинхронный и синхронный запуск)
│   ├── api/
│   │   ├── schemas.py                 # Pydantic DTO (SolveRequest, SolveResultResponse)
│   │   └── router.py                  # Эндпоинты /solve, /{id}/result, /datasets, /parse-uspu
│   └── generator/
│       ├── synthetic.py               # Генератор синтетических данных (Reverse generation)
│       └── uspu_parser.py             # Парсер расписания с сайта uspu.ru
├── scripts/
│   ├── run_benchmarks.py              # CLI кафедрального бенчмарка
│   └── run_parse_uspu.py              # Скрипт парсинга данных с uspu.ru
└── tests/
    ├── test_constraints.py            # 5 тестов правил через ConstraintVerifier
    ├── test_schemas.py                # Тест сериализации DTO и маппинга
    ├── test_synthetic.py              # Тест генератора идеального расписания
    ├── test_api.py                    # 4 теста эндпоинтов (Sync, Async, Health, 404)
    └── test_uspu_parser.py            # Тест парсера данных УрГПУ
```

## 3. Запуск веб-интерфейса и API
```powershell
# Запуск dev-сервера
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Веб-интерфейс: [http://localhost:8000/ui](http://localhost:8000/ui)
- Swagger документация: [http://localhost:8000/docs](http://localhost:8000/docs)

## 4. Запуск полного набора тестов
```powershell
.\.venv\Scripts\pytest -o pythonpath=. tests -v
```
Статус: **12 passed**.
