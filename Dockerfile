FROM python:3.10-slim

# Set up a new user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements first for better caching
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy everything else
COPY --chown=user . $HOME/app

# HF Spaces Docker SDK expects port 7860
EXPOSE 7860

CMD ["python", "start.py"]
