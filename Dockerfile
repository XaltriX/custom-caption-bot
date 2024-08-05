# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y ffmpeg

# Copy the rest of the application code
COPY . .

# Specify the command to run the bot
CMD ["python", "bot.py"]
