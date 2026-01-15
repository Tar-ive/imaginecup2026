FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY mcp_servers/finance_data/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY mcp_servers/finance_data/server.py .

# Copy shared modules
COPY database /app/database

EXPOSE 3003

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3003"]
