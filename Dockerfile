FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir \
    aiogram>=3.0.0 \
    pyTelegramBotAPI \
    requests \
    aiohttp-socks
    python-dotenv

CMD ["python", "Stars"]


