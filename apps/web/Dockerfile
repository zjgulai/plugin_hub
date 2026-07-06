FROM node:22-alpine

WORKDIR /app

RUN corepack enable

ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
ENV NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @plugin-hub/web...

COPY apps/web ./apps/web
RUN pnpm --filter @plugin-hub/web build

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

EXPOSE 3000

CMD ["pnpm", "--filter", "@plugin-hub/web", "start"]
