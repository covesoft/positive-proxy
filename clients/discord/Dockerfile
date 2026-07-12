FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    curl \
    libvips \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    discord.py \
    python-dotenv \
    discord-beacon==4.1.9 \
    httpx

COPY . .

CMD ["python", "main.py"]