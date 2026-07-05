FROM node:18-alpine@sha256:8d6421d663b4c28fd3ebc498332f249011d118945588d0a35cb9bc4b8ca09d9e  # node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 8006

CMD ["node", "src/socket/index.js"]
