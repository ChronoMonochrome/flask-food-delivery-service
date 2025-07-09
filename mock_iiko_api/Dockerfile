# mock_iiko_api/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_iiko_api/app.py .

EXPOSE 5000

CMD ["python", "app.py"]
