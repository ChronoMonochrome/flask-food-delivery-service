# back/mock_iiko_api/Dockerfile (Corrected)
FROM python:3.9-slim-buster

WORKDIR /app

# These paths are now relative to the build context (back/mock_iiko_api)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
