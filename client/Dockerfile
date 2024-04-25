# Dockerfile

FROM node:14 as build-deps
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

COPY env.sh ./
RUN chmod +x ./env.sh

RUN npm install -g serve
CMD ["/bin/bash", "-c", "./env.sh && serve -s build -l 3000"]

# FROM nginx:1.17.8-alpine
# COPY --from=build-deps /usr/src/app/build /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]