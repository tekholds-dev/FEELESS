# FEELESS backend, always-on: the 4 API services + every engine loop (runners, Arena, tier cards, keeper, FeeCat, candles) + the
# Circle signer sidecar, in ONE container. Data (backend/data) must live on a persistent volume mounted at /app/backend/data.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements-feeless.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt -r backend/requirements-feeless.txt
COPY circle/package.json circle/package-lock.json circle/
RUN cd circle && npm ci --omit=dev
COPY backend backend
COPY circle circle
COPY deploy/run-all.sh deploy/run-all.sh
ENV PYTHONUNBUFFERED=1
EXPOSE 5001 5077 5088 5099
CMD ["bash", "deploy/run-all.sh"]
