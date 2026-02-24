# Agente de Newsletter Semanal para WhatsApp

Este projeto implementa um agente que respeita seu processo editorial:

1. Gera sugestões de temas diariamente.
2. Monta a newsletter em formato de caso clínico ou notícia.
3. Envia para você aprovar.
4. Só dispara nos grupos após aprovação.

## Guia completo de instalação

Se você já criou apenas o bot do Telegram e quer o passo a passo do resto (Railway + Z-API), use este guia:

- **`docs/instalacao-telegram-railway-zapi.md`**

## Execução local rápida

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic
python -m uvicorn src.server:app --reload --port 8000
```
