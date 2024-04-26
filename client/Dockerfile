# Dockerfile

FROM node:14 as build-deps
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

COPY set-env.js ./
RUN chmod +x ./set-env.js

RUN npm install -g serve
CMD ["/bin/bash", "-c", "node set-env.js && serve -s build -l 3000"]