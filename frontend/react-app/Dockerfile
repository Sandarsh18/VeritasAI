### Build stage
FROM node:20 AS build
WORKDIR /app
# In Docker, the frontend talks to the backend through nginx's /api proxy on
# the SAME origin, so the baked-in base URL must be empty -> relative paths.
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
# copy package.json first to leverage caching; package-lock optional
COPY package.json ./
RUN npm install --legacy-peer-deps
COPY . /app
RUN npm run build

### Production stage
FROM nginx:alpine
# bash for any shell scripts, curl for the compose healthcheck
RUN apk add --no-cache bash curl
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
