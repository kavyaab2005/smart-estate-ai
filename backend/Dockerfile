FROM python:3.11-slim

# System programs needed by pytesseract and pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr poppler-utils build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs the app as user 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR /home/user/app

# CPU-only torch first (the default Linux wheel is huge)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]