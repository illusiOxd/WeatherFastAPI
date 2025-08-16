# 1. Базовый образ Python
FROM python:3.12-slim

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Копируем зависимости
COPY requirements.txt .

# 4. Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем код приложения
COPY . .

# 6. Экспортируем порт (тот, который использует uvicorn)
EXPOSE 8000

# 7. Команда для запуска приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

