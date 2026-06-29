# Dev-oriented image; docker-compose runs `npm run dev` with a bind mount.
# For production, switch to a multi-stage build using Next.js standalone output.
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
