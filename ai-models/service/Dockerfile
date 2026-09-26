FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY service ./service
COPY models ./models

ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV MODEL_PATH=models/graduate_admission_model.joblib

EXPOSE 8001

CMD ["sh", "-c", "uvicorn service.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
