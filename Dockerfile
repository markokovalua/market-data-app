FROM python:3.12-slim

#RUN apt-get update && apt-get install -y \
#    build-essential \
#    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.111.1 uvicorn[standard]==0.23.2 aiofiles==23.2.1

COPY . .

EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
