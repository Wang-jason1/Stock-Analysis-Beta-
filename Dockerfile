FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for torch or other libs)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Environment variable for Ollama URL
ENV OLLAMA_URL=http://ollama:11434

# CMD will run the FastAPI web server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
