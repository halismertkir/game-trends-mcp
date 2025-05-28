FROM python:3.11-slim

WORKDIR /app

# lxml gibi paketler için sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Önce requirements.txt dosyasını kopyala (Docker önbelleğini daha iyi kullanmak için)
COPY requirements.txt .

# Python bağımlılıklarını yükle
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunun geri kalanını kopyala
COPY . .

# Root olmayan bir kullanıcı oluştur ve ona geç
RUN groupadd -r appuser && useradd -r -g appuser appuser
# /app dizininin appuser'a ait olduğundan emin ol
RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1

# Uygulamayı çalıştıracak komut
CMD ["python", "server.py"]