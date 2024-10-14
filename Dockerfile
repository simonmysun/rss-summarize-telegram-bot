FROM python:alpine3.20

COPY . /app/

WORKDIR /app/

RUN pip install -q -r requirements.txt

CMD ["python", "main.py"]