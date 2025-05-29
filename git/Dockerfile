# Use a base Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install necessary packages
RUN apt-get update && \
    apt-get install -y gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script and model
COPY ddos_detection.py .
COPY ddos_detection_model.pkl .
COPY train_sample.csv .



# Run the script when the container starts
CMD ["python", "ddos_detection.py"]
