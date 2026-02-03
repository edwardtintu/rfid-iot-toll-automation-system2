# 1. Base image with Python
FROM python:3.10-slim

# 2. Set working directory inside container
WORKDIR /app

# 3. Copy requirements first (for caching)
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install psycopg2-binary

# 5. Copy backend source code
COPY . .

# 6. Create storage directories
RUN mkdir -p backend/storage
RUN mkdir -p /app/storage
RUN mkdir -p backend/blockchain_contracts/output

# 7. Expose FastAPI port
EXPOSE 8000

# 8. Run FastAPI app
CMD ["sh", "-c", "export USE_POSTGRES=true && uvicorn app:app --host 0.0.0.0 --port 8000 --reload"]