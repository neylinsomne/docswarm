FROM python:3.12-slim

WORKDIR /app

# Copy metadata first for layer caching, then install the engine + dev/yaml extras.
COPY pyproject.toml README.md ./
COPY docswarm ./docswarm
RUN pip install --no-cache-dir -e ".[yaml,dev]"

COPY . .

# Default: run the offline demo. Override in compose for an interactive shell.
CMD ["python", "-m", "examples.informe_demo.run"]
