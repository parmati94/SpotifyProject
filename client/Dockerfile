# Dockerfile

FROM node:14 as build-deps
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm setup
COPY . ./
RUN npm run build

# FROM nginx:1.17.8-alpine
# COPY --from=build-deps /usr/src/app/build /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]