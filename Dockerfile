 
FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED True
ENV LANG C.UTF-8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "./bot.py"]