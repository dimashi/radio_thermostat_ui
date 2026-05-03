FROM python:3.12-slim

WORKDIR /app

# Copy all artifacts and requirements from build/.dist folder
COPY build/.dist/ .

# Install dependencies
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy client directory  
COPY client/components/table_scheduler/ /app/client/components/table_scheduler/

# Set Python path
ENV PYTHONPATH=/app/server

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "controller:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/server"]
