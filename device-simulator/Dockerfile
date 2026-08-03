FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator files
COPY . .

# Run the publisher script
CMD ["python", "drone_publisher.py"]
