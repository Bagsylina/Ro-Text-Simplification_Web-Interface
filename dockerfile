# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set memory-related environment variables
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/cache/transformers
ENV HF_HOME=/app/cache/huggingface
ENV TORCH_HOME=/app/cache/torch

# Create cache directories
RUN mkdir -p /app/cache/transformers /app/cache/huggingface /app/cache/torch

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with memory optimization
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download models in separate layers to optimize memory usage
RUN python -m spacy download ro_core_news_lg

# Pre-download fasttext model to reduce startup time
#RUN python -c "import fasttext.util; fasttext.util.download_model('ro', if_exists='ignore')"

# Copy application code
#COPY . .
COPY app.py /app/
COPY model.py /app/
COPY --chown=flaskuser:flaskuser templates/ /app/templates/ 
COPY --chown=flaskuser:flaskuser dex-online-database/ /app/dex-online-database/
COPY --chown=flaskuser:flaskuser scraping/ /app/scraping/

# Create a non-root user
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app
USER flaskuser

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]