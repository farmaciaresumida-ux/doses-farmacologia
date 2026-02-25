# Agente de Newsletter Semanal para WhatsApp

Este projeto implementa um agente que respeita seu processo editorial:

1. Gera sugestões de temas diariamente.
2. Monta a newsletter em formato de caso clínico ou notícia.
3. Envia para você aprovar.
4. Só dispara nos grupos após aprovação.

## Onde preencher a API key da OpenAI?

Preencha na variável de ambiente:

- `OPENAI_API_KEY`

Exemplos de onde configurar:
- Local: arquivo `.env` (copiando de `.env.example`).
- Railway: aba **Variables** do serviço.

Também pode configurar o modelo em:
- `OPENAI_MODEL` (padrão: `gpt-4o-mini`).

## Guia completo de instalação

Se você já criou apenas o bot do Telegram e quer o passo a passo do resto (Railway + Z-API), use este guia:

- **`docs/instalacao-telegram-railway-zapi.md`**

## Execução local rápida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.server:app --reload --port 8000
```


## Como fazer teste real (Telegram + Z-API)

1. Verifique status da integração:

```bash
curl -sS https://SEU_APP.up.railway.app/status
```

2. Dispare um teste real agora (manda 1 mensagem no Telegram do dono e 1 no primeiro grupo da lista):

```bash
curl -sS -X POST https://SEU_APP.up.railway.app/test-real
```

3. Gere newsletter do dia:

```bash
curl -sS -X POST https://SEU_APP.up.railway.app/run-daily
```

4. Aprove com o `draft_id` retornado:

```bash
curl -sS -X POST https://SEU_APP.up.railway.app/approval \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"draft-2026-02-24","approved":true}'
```


## Por que o /start não responde?

Porque o Telegram só entrega comandos para o seu backend se você configurar webhook.

1. Faça deploy da versão atual.
2. Configure o webhook (substitua TOKEN e URL):

```bash
curl -sS "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://SEU_APP.up.railway.app/telegram/webhook"
```

3. Teste no Telegram com `/start`.

Comandos suportados no chat:
- `/start`
- `/status`
- `/test-real`
- `/run-daily`
