FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN  pip install --no-cache-dir \
    agent-framework==1.0.0b251223 \
    agent-framework-azure-ai==1.0.0b251223 \
    azure-identity>=1.15.0

# Copy agent code
COPY agent.py .

# Run agent
CMD ["python", "agent.py"]