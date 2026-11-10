# Flask app image. The same image runs locally, on EC2, and against RDS.
FROM python:3.12-slim

WORKDIR /srv
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/
COPY db/ db/
COPY tests/ tests/

WORKDIR /srv/app
EXPOSE 8000
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "app:app"]
