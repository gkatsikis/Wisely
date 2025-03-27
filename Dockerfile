FROM python:3.13.2

WORKDIR /code

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
