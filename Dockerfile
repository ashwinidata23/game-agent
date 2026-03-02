FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Output directory — mount as volume to persist generated files on host
RUN mkdir -p /app/output

# Environment variable for output path
ENV OUTPUT_DIR=/app/output

# Run interactively — user types game idea and answers clarification questions
ENTRYPOINT ["python", "main.py"]