FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better layer caching.
COPY package.json ./
COPY scripts/copy-cesium.mjs scripts/copy-cesium.mjs
RUN npm install

# Copy the rest of the app source.
COPY . .

# Cesium static assets (workers, widgets, assets) are served from /cesium.
# The predev script copies them into public/ before the dev server starts.

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
