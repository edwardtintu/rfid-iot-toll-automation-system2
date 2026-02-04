FROM python:3.10-slim

WORKDIR /app

# Copy requirements from backend folder
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

EXPOSE 8000

CMD ["python", "app.py"]