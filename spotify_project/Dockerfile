# Dockerfile

FROM python:3.8-slim-buster
WORKDIR /app

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Install dependencies:
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy python files:
COPY . spotify_project/

# Run the application:
CMD ["uvicorn", "spotify_project.api.controller:app", "--host", "0.0.0.0", "--port", "8000"]