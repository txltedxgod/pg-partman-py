FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pg_partman ./pg_partman
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["pg-partman"]
CMD ["--config=/etc/pg-partman/config.yaml"]
