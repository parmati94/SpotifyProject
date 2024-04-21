# Dockerfile

FROM python:3.8-slim-buster
WORKDIR /app/spotify_project

# Set PYTHONPATH
ENV PYTHONPATH=/app/spotify_project

# Install dependencies:
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy python files:
COPY . .

# Run the application:
CMD ["uvicorn", "api.controller:app", "--host", "0.0.0.0", "--port", "8000"]