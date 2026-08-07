FROM python:3.12-slim

WORKDIR /app

# Set timezone to EST
ENV TZ=America/New_York

# Copy all artifacts and requirements from build/.dist folder
COPY build/.dist/src .
COPY build/.dist/requirements-minimal.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy client directory  
# COPY src/client/components/table_scheduler/ /app/client/components/table_scheduler/

# Set Python path
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "thermo_ui_app:app", "--host", "0.0.0.0", "--port", "8080"]
