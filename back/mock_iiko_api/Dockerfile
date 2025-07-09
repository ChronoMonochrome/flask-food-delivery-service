# mock_iiko_api/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY back/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY back/mock_iiko_api/app.py .

EXPOSE 5000

CMD ["python", "app.py"]
