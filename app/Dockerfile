FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Используем gunicorn для production‑режима, но сейчас можно и python app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
