FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    uvicorn>=0.27.0 \
    xgboost>=2.0.0 \
    shap>=0.44.0 \
    scikit-learn>=1.4.0 \
    pandas>=2.0.0 \
    numpy>=1.26.0 \
    joblib \
    redis>=5.0.0

# Copy API source
COPY api/ ./api/
COPY model/ ./model/

ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
