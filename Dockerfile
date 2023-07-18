FROM mambaorg/micromamba:0.15.3
USER root
RUN apt-get update && DEBIAN_FRONTEND=“noninteractive” apt-get install -y --no-install-recommends \
       nginx \
       ca-certificates \
       apache2-utils \
       certbot \
       python3-certbot-nginx \
       sudo \
       cifs-utils \
       && \
    rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get -y install cron
RUN mkdir /opt/chatbot
RUN chmod -R 777 /opt/chatbot
WORKDIR /opt/chatbot
USER micromamba
EXPOSE 8000
COPY environment.yml environment.yml
RUN micromamba install -y -n base -f environment.yml && \
   micromamba clean --all --yes
COPY streamlit_app streamlit_app
ENTRYPOINT ["streamlit", "run"]
CMD ["./streamlit_app/main.py","--server.port","8000","--theme.base","dark"]

