FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-llm.txt ./
ARG WITH_LLM=false
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$WITH_LLM" = "true" ]; then pip install --no-cache-dir -r requirements-llm.txt; fi && \
    python -m pip check && \
    useradd -r -u 10001 civitas
COPY --chown=civitas:civitas app/ app/
COPY --chown=civitas:civitas frontend/ frontend/
COPY --chown=civitas:civitas evals/ evals/
RUN mkdir /app/data && chown civitas:civitas /app/data
USER civitas
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health',timeout=3)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
