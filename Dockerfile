FROM python:3.11-slim

WORKDIR /app

# torch тянется sentence-transformers, а по умолчанию на Linux ставится с полным
# набором CUDA-библиотек (nvidia-cu13-*, несколько ГБ) даже без GPU в образе.
# Ставим CPU-only колесо заранее, чтобы sentence-transformers его просто переиспользовал.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Держите список в синхроне с pyproject.toml: [project.dependencies] + [project.optional-dependencies].dev
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "pydantic>=2.0.0" \
    "python-dotenv>=1.0.0" \
    "httpx[socks]>=0.27.0" \
    "openai>=1.50.0" \
    "chromadb>=0.5.0" \
    "sentence-transformers>=3.0.0" \
    "asyncpg>=0.29.0" \
    "pytest>=8.0.0" \
    "pytest-cov>=5.0.0" \
    "pytest-asyncio>=0.24.0"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
