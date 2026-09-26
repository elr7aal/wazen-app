FROM ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git unzip xz-utils libglu1-mesa python3 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch stable https://github.com/flutter/flutter.git /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter config --enable-web --no-analytics
WORKDIR /app
COPY pubspec.yaml ./
RUN flutter pub get
COPY lib ./lib
COPY test ./test
RUN flutter create --platforms=web --project-name=wazen_mobile .
COPY prepare_web.py ./
RUN python3 prepare_web.py && flutter test
ARG API_BASE_URL
RUN test -n "$API_BASE_URL" && flutter build web --release --dart-define="API_BASE_URL=$API_BASE_URL"
FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
