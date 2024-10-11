FROM python:3.11

WORKDIR /root/healbot.lol

COPY . /root/healbot.lol

RUN apt update -y && apt install -y ffmpeg
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5432
CMD ["python", "./main.py"]