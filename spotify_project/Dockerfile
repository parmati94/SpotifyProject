# Dockerfile

FROM python:3.8-slim-buster
WORKDIR /app

# Install dependencies:
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy python files:
COPY . .

# Run the application:
CMD ["uvicorn", "controller:app", "--host", "0.0.0.0", "--port", "8000"]