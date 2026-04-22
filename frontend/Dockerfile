# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Copia arquivos de dependências
COPY package*.json ./
RUN npm install

# Copia código fonte
COPY . .

# Build da aplicação
RUN npm run build

# Stage 2: Runtime (Nginx)
FROM nginx:alpine

# Copia o build para o diretório de arquivos estáticos do Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copia configuração básica do Nginx (opcional, mas boa prática)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
