FROM mysql:8.0

# Set timezone
ENV TZ=America/Argentina/Buenos_Aires
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy initialization scripts
COPY ./init /docker-entrypoint-initdb.d

EXPOSE 3306
