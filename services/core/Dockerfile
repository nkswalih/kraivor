FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/base.txt

COPY . /app/

EXPOSE 8002

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8002"]
