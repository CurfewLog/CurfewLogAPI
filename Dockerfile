FROM python:3.6

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN pip install gunicorn

COPY . /code
WORKDIR /code

CMD gunicorn app:app -b :8080
