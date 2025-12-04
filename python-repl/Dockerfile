FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY repl.py ingest.py ./

CMD ["python", "repl.py"]
