FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    agent-framework>=1.0.0 \
    agent-framework-azure-ai>=1.0.0 \
    azure-identity>=1.15.0 \
    azure-ai-openai>=1.0.0

COPY agent.py .

EXPOSE 8082

CMD ["python", "agent.py"]