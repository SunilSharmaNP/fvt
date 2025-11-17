FROM python:3.10-slim

WORKDIR /app

# ffmpeg aur mediainfo install karein
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    mediainfo \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies install karein
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki code copy karein
COPY . .

# Bot run karein
CMD ["python", "bot.py"]