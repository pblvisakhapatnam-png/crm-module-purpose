FROM node:20-alpine

WORKDIR /app

# Install from the lockfile so the image is reproducible and matches the reviewed dependency set.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

RUN npm run build

EXPOSE 3000

# `vite preview` serves the built application from dist/ on port 3000. It applies the SPA
# fallback, so a direct request or reload of a deep link such as /work-orders/<id> returns
# index.html rather than a server 404, and it applies the /api proxy from vite.config.ts, so
# browser code keeps calling relative /api URLs.
CMD ["npm", "run", "preview"]
