FROM node:24-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci

# App source (overlaid by the bind mount at runtime; node_modules preserved via a volume)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
