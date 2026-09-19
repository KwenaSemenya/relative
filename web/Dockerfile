FROM node:22-slim AS build

WORKDIR /srv
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev


FROM node:22-slim

ENV NODE_ENV=production \
    PORT=8080

WORKDIR /srv
COPY --from=build /srv/build ./build
COPY --from=build /srv/node_modules ./node_modules
COPY --from=build /srv/package.json ./

EXPOSE 8080
CMD ["node", "build"]
