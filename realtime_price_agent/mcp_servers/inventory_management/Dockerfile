FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY mcp_servers/inventory_management/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY mcp_servers/inventory_management/server.py .

# Copy shared modules
COPY database /app/database
COPY services /app/services

EXPOSE 3002

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3002"]
