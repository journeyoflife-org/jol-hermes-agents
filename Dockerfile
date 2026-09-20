# Hermes — declarative agent definition + validator image.
# Audit finding H3: hardened per mandate §3.2 (non-root, healthcheck,
# no secrets baked in; secrets arrive via env_file at runtime).
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 hermes

WORKDIR /app

# Install first for layer caching; pyproject pins the dependency set.
COPY pyproject.toml README.md main.py ./
COPY config ./config
COPY skills ./skills
COPY memory ./memory
COPY prompts ./prompts
COPY context ./context
RUN pip install --no-cache-dir . \
    && mkdir -p /var/lib/hermes \
    && chown -R hermes:hermes /app /var/lib/hermes

USER hermes

ENV HERMES_MEMORY_PATH=/var/lib/hermes/hermes-memory.sqlite

# Declarative artefacts must stay self-consistent inside the image.
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD ["python", "main.py", "validate"]

ENTRYPOINT ["hermes"]
