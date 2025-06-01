FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /root/.local/share/argos-translate/packages
COPY files/translate-en_sv-1_5.argosmodel /root/.local/share/argos-translate/packages/
COPY files/translate-sv_en-1_5.argosmodel /root/.local/share/argos-translate/packages/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
