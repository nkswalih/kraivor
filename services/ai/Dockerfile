FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/base.txt

COPY . /app/

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
