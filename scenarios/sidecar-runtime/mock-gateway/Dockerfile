FROM node:18-alpine
WORKDIR /app
COPY server.js .
EXPOSE 8080
# Run as the unprivileged `node` user shipped in the base image rather than
# root (docker:S6471). Mock dev gateway: binds 8080 (>1024) and only reads
# the copied server.js, so a non-root user is sufficient.
USER node
CMD ["node", "server.js"]
