FROM python:3.12-slim

# Set working directory
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

# Copy only requirements first for better cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port
EXPOSE 5000

# Run Gunicorn with 4 workers
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app", "--access-logfile", "-", "--error-logfile", "-"]
