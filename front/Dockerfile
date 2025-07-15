FROM node:18.16.0-slim as build-env

ARG MODE
ARG GITLAB_ADDRESS
ARG GITLAB_TOKEN

WORKDIR /app
COPY package.json ./
COPY *.lock ./

RUN npm install --force
COPY . ./

RUN npm run build:$MODE

# production environment
FROM nginx:stable-alpine
# nginx conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build-env /app/build /var/www/html
CMD ["nginx", "-g", "daemon off;"]