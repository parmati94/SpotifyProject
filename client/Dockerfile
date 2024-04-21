# Dockerfile

FROM node:14 as build-deps
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

ENV REACT_APP_API_BASE_URL=http://api:8000

RUN npm install -g serve
CMD serve -s build -l 3000

# FROM nginx:1.17.8-alpine
# COPY --from=build-deps /usr/src/app/build /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]