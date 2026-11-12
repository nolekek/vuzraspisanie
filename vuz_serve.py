import os
import sys
import uvicorn

# Гарантируем, что корневая папка проекта первой залетает в sys.path,
# откуда бы ты этот скрипт ни вызывал (хоть из System32, хоть из жопы)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    print(f"🚀 Запуск VUZ Timetable Solver из: {PROJECT_ROOT}")
    print("📍 Доступ: http://localhost:8000/ (Swagger: /docs, UI: /ui)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
