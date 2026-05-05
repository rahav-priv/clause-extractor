FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

RUN mkdir -p /data

ENV CLAUSE_EXTRACTOR_PORT=6363
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////data/contracts.db

VOLUME ["/data"]

EXPOSE 6363

CMD ["python", "server/main.py"]
