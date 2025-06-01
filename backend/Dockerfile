FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /root/.local/share/argos-translate/packages
COPY files/translate-en_sv-1_5.argosmodel /root/.local/share/argos-translate/packages/
COPY files/translate-sv_en-1_5.argosmodel /root/.local/share/argos-translate/packages/

# Установить модели сразу при сборке
RUN python3 -c "\
import argostranslate.package;\
argostranslate.package.install_from_path('/root/.local/share/argos-translate/packages/translate-en_sv-1_5.argosmodel');\
argostranslate.package.install_from_path('/root/.local/share/argos-translate/packages/translate-sv_en-1_5.argosmodel')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
