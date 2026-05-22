FROM grafana/loki:3.0.0

# Copie de la configuration GCP
COPY loki-config.yml /etc/loki/local-config.yaml

# Commande d'exécution par défaut requise par Loki
CMD ["-config.file=/etc/loki/local-config.yaml"]