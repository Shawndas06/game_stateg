FROM node:22-alpine AS client
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt && useradd --create-home campaign
COPY campaign/ campaign/
COPY server/ server/
COPY --from=client /build/web/dist/ web/dist/
COPY web/public/land.geojson web/public/land.geojson
COPY web/public/bithynia-geography.json web/public/bithynia-geography.json
COPY web/public/mediterranean-geography.json web/public/mediterranean-geography.json
USER campaign
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn server.app:create_app --factory --host 0.0.0.0 --port \"${PORT:-8000}\""]
