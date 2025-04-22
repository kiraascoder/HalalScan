# Gunakan base image Python versi terbaru (misal Python 3.12 slim)
FROM python:3.12-slim

# Install dependencies sistem yang diperlukan untuk OpenCV dan libGL
RUN apt-get update && apt-get install -y \
    libgl1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set working directory di dalam container
WORKDIR /app

# Copy requirements.txt dulu agar cache pip bisa digunakan dengan baik
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file project ke container
COPY . .

# Expose port sesuai yang digunakan Flask (biasanya 5000)
EXPOSE 5000

# Set environment variable supaya Flask jalan di 0.0.0.0, bukan localhost
ENV FLASK_RUN_HOST=0.0.0.0

# Command untuk menjalankan aplikasi Flask (ubah sesuai file utama Flask kamu)
CMD ["flask", "run"]
