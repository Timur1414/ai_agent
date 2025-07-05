FROM python:latest
LABEL authors="timat"

RUN apt-get update && apt-get install -y

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
COPY prompts.py .
COPY .env .

CMD ["python", "main.py"]

#  Команда создания образа                              docker build .
#  Команда просмотра всех образов                       docker images
#  Команда запуска контейнера в интерактивном режиме    docker run -it 1351055fd55a