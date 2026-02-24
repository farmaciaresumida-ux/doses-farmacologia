# Guia de Instalação (Telegram + Railway + Z-API)

Este guia foi feito para o cenário em que você **já criou o bot no Telegram** e quer configurar todo o resto do zero.

Objetivo final:
1. Você recebe no Telegram sugestões + newsletter pronta.
2. Você aprova/reprova no Telegram.
3. Se aprovar, o sistema dispara nos grupos de WhatsApp via Z-API.
4. O projeto fica rodando 24h no Railway (plano gratuito enquanto houver crédito free).

---

## 1) Pré-requisitos

Antes de começar, você precisa ter:

- Conta no **GitHub**.
- Conta no **Railway** (https://railway.app/).
- Conta no **Z-API** (https://z-api.io/).
- Seu **bot do Telegram** já criado no BotFather.
- Python 3.11+ instalado (para testes locais).

---

## 2) Tokens e dados que você vai separar

### 2.1 Telegram
No BotFather, pegue:
- `TELEGRAM_BOT_TOKEN`

Para descobrir seu `TELEGRAM_CHAT_ID`:
1. Abra conversa com seu bot e envie `/start`.
2. Acesse no navegador:
   `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
3. Procure o campo `chat` → `id`.

> Esse chat_id é onde o agente vai pedir aprovação diariamente.

### 2.2 Z-API (WhatsApp)
No painel da Z-API, copie:
- `ZAPI_INSTANCE_ID`
- `ZAPI_INSTANCE_TOKEN`
- `ZAPI_SECURITY_TOKEN` (quando habilitado)

Também deixe anotado os IDs dos grupos de WhatsApp que vão receber a newsletter.

---

## 3) Estrutura mínima de variáveis de ambiente

No Railway você vai configurar estas variáveis:

- `OWNER_TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_TOKEN`
- `GROUP_IDS` (separados por vírgula)
- `BUSINESS_CONTEXT`
- `ZAPI_INSTANCE_ID`
- `ZAPI_INSTANCE_TOKEN`
- `ZAPI_SECURITY_TOKEN`
- `RUN_HOUR_BRT` (ex.: 8)

Exemplo:

```env
OWNER_TELEGRAM_CHAT_ID=8430315363
TELEGRAM_BOT_TOKEN=8482503703:AAELAzVFrHX10JJmdXqP0y6k0vee2oEN5lA8482503703:AAELAzVFrHX10JJmdXqP0y6k0vee2oEN5lA
GROUP_IDS=1203630xxxxxxxx@g.us,1203630yyyyyyyy@g.us
BUSINESS_CONTEXT=farmacologia clínica aplicada
ZAPI_INSTANCE_ID=3EF3E7A38E7D416AC61C32059B4CF0B7
ZAPI_INSTANCE_TOKEN=E14C60A36543067BFB3F0D82
ZAPI_SECURITY_TOKEN=SEU_SECURITY_TOKEN
RUN_HOUR_BRT=8
```

---

## 4) Publicar o projeto no GitHub

No seu computador (pasta do projeto):

```bash
git add .
git commit -m "docs: adiciona guia de instalação telegram + railway + zapi"
git push origin work
```

Se ainda não tiver remoto configurado, crie o repositório no GitHub e conecte:

```bash
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin work
```

---

## 5) Deploy no Railway (gratuito)

1. Entre em https://railway.app/.
2. Clique em **New Project**.
3. Selecione **Deploy from GitHub Repo**.
4. Escolha seu repositório.
5. No serviço criado, abra **Variables** e cole todas as variáveis do passo 3.
6. Em **Settings**, confira o comando de start.
   - Exemplo comum: `python -m uvicorn src.server:app --host 0.0.0.0 --port $PORT`
7. Faça deploy.
8. Abra os logs para verificar se iniciou sem erro.

---

## 6) Conectar o WhatsApp na Z-API

1. No painel da Z-API, abra sua instância.
2. Escaneie o QR Code com o número que fará os disparos.
3. Aguarde status “connected”.
4. Teste envio de mensagem pelo painel da Z-API.
5. Confirme que o número já está nos grupos de destino.

---

## 7) Fluxo diário de aprovação (operação)

Fluxo sugerido:

1. Scheduler roda diariamente.
2. Bot te envia no Telegram:
   - sugestões de temas
   - newsletter pronta
   - botões/comandos de aprovação
3. Você aprova.
4. Sistema dispara automaticamente nos grupos de `GROUP_IDS` via Z-API.

---

## 8) Teste ponta a ponta (checklist)

1. Faça um disparo manual do draft (endpoint/manual run).
2. Verifique se chegou no Telegram.
3. Aprove o draft.
4. Verifique se chegou nos grupos do WhatsApp.
5. Reprove outro draft para validar que não dispara.

Se tudo acima funcionar, seu pipeline está pronto.

---

## 9) Troubleshooting rápido

### Erro no Telegram
- Token inválido: recrie no BotFather.
- Chat ID errado: rode `getUpdates` novamente após enviar `/start`.

### Erro na Z-API
- Instância desconectada: reconectar QR Code.
- Token inválido: copiar novamente credenciais da instância.
- Grupo não recebe: verificar se o número da instância está no grupo.

### Erro no Railway
- App não sobe: conferir command/start e logs.
- Variável ausente: revisar seção Variables.

---

## 10) Custos e limites (importante)

- **Railway**: pode ter créditos gratuitos limitados por mês.
- **Z-API**: normalmente possui trial/plano com limites.
- **Telegram Bot API**: gratuito para uso comum.

---

## 11) Próximo passo recomendado

Depois que isso estiver funcionando, o próximo upgrade é:

1. Persistir drafts/aprovações em banco (Postgres).
2. Criar painel simples para histórico de newsletters.
3. Adicionar fila/retry para falha de envio no WhatsApp.
4. Configurar observabilidade (logs + alertas no Telegram).
