# ratings-v2/Dockerfile
FROM node:20-alpine

WORKDIR /opt/microservices/ratings
COPY ratings.js .

# httpdispatcher is the only external dep
RUN npm init -y && npm i httpdispatcher

EXPOSE 9080
CMD ["node", "ratings.js", "9080"]