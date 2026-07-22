FROM node:20-alpine

WORKDIR /app

# Install dependencies (layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy application code
COPY . .

# Run Vite dev server with hot-reload, listening on all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
