FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./
EXPOSE 8000
# Gunicorn (single worker for comparability; tune in bench)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "wsgi:application"]

