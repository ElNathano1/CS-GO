# === Etape 1 : Choisir l'image Python ===
FROM python:3.13-slim

# === Etape 2 : Definir le repertoire de travail ===
WORKDIR /app

# === Etape 3 : Copier les fichiers necessaires ===
COPY requirements.txt .
COPY . .

# === Etape 4 : Installer les dependances ===
RUN pip install --no-cache-dir -r requirements.txt

# === Etape 5 : Creer un dossier pour les uploads ===
RUN mkdir -p /data/uploads

# === Etape 6 : Exposer le port FastAPI ===
EXPOSE 8000

# === Etape 7 : Lancer l'application ===
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"