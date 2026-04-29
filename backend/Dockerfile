# Backend service Docker image
FROM node:18-alpine

# App directory inside the container
WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm install --omit=dev

# Copy the rest of the backend source
COPY . .

# Backend API listens on port 5000
EXPOSE 5000

# Start the Node.js API (expects server.js in backend/)
CMD ["node", "server.js"]
