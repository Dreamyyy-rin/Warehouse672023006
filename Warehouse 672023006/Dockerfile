FROM python:3.11.8-slim-bullseye As builder

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y libpq-dev gcc

Run python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
Run pip install -r requirements.txt

FROM python:3.11.8-slim-bullseye

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y libpq-dev
Run rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV CLOUD_APPS CLOUD_RUN

WORKDIR /pythonproject
COPY . ./
CMD . /opt/venv/bin/activate && exec gunicorn --worker-class eventlet --bind 0.0.0.0:8080 --workers 1 -t 60 app:app