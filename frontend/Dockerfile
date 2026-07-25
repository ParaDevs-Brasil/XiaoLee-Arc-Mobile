FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_CORE_API_URL
ARG NEXT_PUBLIC_WEB3AUTH_CLIENT_ID
ARG NEXT_PUBLIC_TELEGRAM_BOT_NAME
ENV NEXT_PUBLIC_CORE_API_URL=$NEXT_PUBLIC_CORE_API_URL
ENV NEXT_PUBLIC_WEB3AUTH_CLIENT_ID=$NEXT_PUBLIC_WEB3AUTH_CLIENT_ID
ENV NEXT_PUBLIC_TELEGRAM_BOT_NAME=$NEXT_PUBLIC_TELEGRAM_BOT_NAME
RUN npm run build

FROM node:18-alpine AS runner
RUN npm install -g serve
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app
COPY --from=builder /app/out ./
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 3000
CMD ["sh", "-c", "serve -s . -l ${PORT:-3000}"]
