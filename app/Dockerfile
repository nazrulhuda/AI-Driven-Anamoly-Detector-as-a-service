FROM python:3.9-slim

WORKDIR /app

COPY report_receiver.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# EXPOSE is optional, but good practice
EXPOSE 8000

CMD ["python", "report_receiver.py"]