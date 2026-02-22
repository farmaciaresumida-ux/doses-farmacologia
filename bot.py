"""
Doses de Farmacologia — Bot Telegram + Agente Newsletter
Farmácia Resumida | Hayandra Costa

Fluxo:
1. Você envia o tema/caso para o bot no Telegram
2. O agente pesquisa fontes clínicas reais no PubMed
3. Claude escreve a newsletter no seu estilo
4. Bot te manda para revisão no Telegram
5. Você clica em "Aprovar e Enviar"
6. Evolution API dispara automaticamente no grupo do WhatsApp
"""

import os
import logging
import anthropic
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────
TELEGRAM_TOKEN     = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
SEU_TELEGRAM_ID    = int(os.environ["SEU_TELEGRAM_ID"])
EVOLUTION_URL      = os.environ["EVOLUTION_URL"]       # ex: https://sua-evolution.railway.app
EVOLUTION_API_KEY  = os.environ["EVOLUTION_API_KEY"]   # chave gerada na Evolution
EVOLUTION_INSTANCE = os.environ["EVOLUTION_INSTANCE"]  # nome da instância conectada
WHATSAPP_GROUP_ID  = os.environ["WHATSAPP_GROUP_ID"]   # ID do grupo (ver GUIA.md)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# PROMPT DO AGENTE
# ─────────────────────────────────────────
SYSTEM_PROMPT = """Você é o agente de escrita da newsletter "Doses de Farmacologia" da Farmácia Resumida, criada pela farmacêutica clínica Hayandra Costa.

IDENTIDADE DA NEWSLETTER:
- Desmonta prescrições comuns com farmacologia clínica rigorosa
- Zero achismo. Toda afirmação baseada em evidências (artigos, diretrizes, bulas, sites oficiais como ANVISA, CFF, PubMed, Nature, UpToDate)
- Tom: direto, crítico, inteligente, sem ser arrogante
- Voz: feminina, clínica, didática — como uma colega sênior que pensa em voz alta
- Público: farmacêuticos e estudantes de farmácia

ESTRUTURA OBRIGATÓRIA (use exatamente esta formatação para WhatsApp):

Se o tema for CASO CLÍNICO:
```
💊 #[N] Doses de Farmacologia
Aqui, prescrições comuns são desmontadas com farmacologia clínica.
Achismo não entra.

🩺 O caso
[descreva o caso clínico de forma concisa]

🧠 O raciocínio
[análise farmacológica clínica detalhada, com mecanismos, riscos, evidências]

📌 A regra
[frase de impacto que resume o aprendizado — curta e memorável]

💊 Pílulas extras
📰 Notícia que me fez parar:
[título relevante + link real]

📚 O que me deixou 1% mais crítica essa semana:
[referência científica real + link PubMed/Nature/periódico]

📖 O que estou estudando:
[livro, capítulo ou fonte de referência relevante ao tema]

💬 E você, qual prescrição te fez parar essa semana?

_Farmacologia clínica é o antídoto contra o achismo._ (Costa, Hay).
```

Se o tema for NOTÍCIA/ATUALIDADE:
```
💊 #[N] Doses de Farmacologia
Aqui, prescrições comuns são desmontadas com farmacologia clínica.
Achismo não entra.

🩺 "[manchete ou frase de impacto sobre a notícia]"
[contexto breve]

🧠 O raciocínio
[análise clínica e farmacológica da notícia, separando sensacionalismo de fato técnico]

Na prática:
• [bullet com implicação clínica real]
• [bullet com implicação clínica real]

📌 A regra
[frase de impacto curta]

💊 Pílulas extras
📰 Notícia que dominou a semana
[título + link real]

📚 Para pensar melhor
[referência científica + link real]

📖 O que estou revisitando
[fonte técnica relevante + link real]

💬 E você?
[pergunta de engajamento relevante ao tema]

_Farmacologia clínica é o antídoto contra o achismo._
```

REGRAS INVIOLÁVEIS:
1. NUNCA invente links. Se não tiver link real, escreva [BUSCAR LINK]
2. Toda afirmação clínica deve ter embasamento identificável
3. Mantenha o tom crítico — questione prescrições, separe crença de evidência
4. Use *negrito* e _itálico_ na formatação do WhatsApp
5. Seja conciso: raciocínio denso, não longo
6. A pergunta final deve provocar reflexão clínica real"""


# ─────────────────────────────────────────
# PUBMED
# ─────────────────────────────────────────
def buscar_pubmed(tema: str, max_results: int = 3) -> list[dict]:
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": tema, "retmax": max_results, "sort": "relevance", "retmode": "json"},
            timeout=10,
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        r2 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
            timeout=10,
        )
        result = r2.json().get("result", {})
        artigos = []
        for uid in ids:
            doc = result.get(uid, {})
            titulo = doc.get("title", "")
            if titulo:
                artigos.append({
                    "titulo": titulo,
                    "journal": doc.get("fulljournalname", ""),
                    "ano": doc.get("pubdate", "")[:4],
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                })
        return artigos
    except Exception as e:
        logger.warning(f"Erro PubMed: {e}")
        return []


# ─────────────────────────────────────────
# GERAÇÃO DA NEWSLETTER
# ─────────────────────────────────────────
def gerar_newsletter(tema: str, numero: int) -> str:
    artigos = buscar_pubmed(tema)
    contexto = ""
    if artigos:
        contexto = "\n\nARTIGOS NO PUBMED (use como referência):\n"
        for a in artigos:
            contexto += f"- {a['titulo']} ({a['journal']}, {a['ano']}) → {a['link']}\n"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Crie a newsletter número {numero} sobre:\n\nTEMA: {tema}{contexto}\n\nIdentifique se é caso clínico ou notícia e use a estrutura correspondente."
        }],
    )
    return response.content[0].text


# ─────────────────────────────────────────
# EVOLUTION API — DISPARO NO WHATSAPP
# ─────────────────────────────────────────
def enviar_whatsapp(texto: str) -> bool:
    try:
        r = requests.post(
            f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}",
            json={"number": WHATSAPP_GROUP_ID, "text": texto},
            headers={"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            logger.info("Newsletter enviada no WhatsApp.")
            return True
        logger.error(f"Erro Evolution API: {r.status_code} — {r.text}")
        return False
    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp: {e}")
        return False


# ─────────────────────────────────────────
# SEGURANÇA
# ─────────────────────────────────────────
def apenas_hayandra(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != SEU_TELEGRAM_ID:
            await update.message.reply_text("⛔ Acesso restrito.")
            return
        return await func(update, context)
    return wrapper


# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────
@apenas_hayandra
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💊 *Doses de Farmacologia — Bot Ativo*\n\n"
        "Me mande o tema:\n\n"
        "`caso: amoxicilina + ciprofloxacino em ITU, homem 52 anos`\n"
        "`notícia: rivotril saiu do mercado`\n\n"
        "/numero — próxima edição\n"
        "/setnumero 15 — definir número\n"
        "/grupoid — ver grupo configurado",
        parse_mode="Markdown",
    )


@apenas_hayandra
async def numero_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = context.bot_data.get("numero", 1)
    await update.message.reply_text(f"📌 Próxima edição: *#{n}*", parse_mode="Markdown")


@apenas_hayandra
async def set_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.args[0])
        context.bot_data["numero"] = n
        await update.message.reply_text(f"✅ Número atualizado para *#{n}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("Use: `/setnumero 15`", parse_mode="Markdown")


@apenas_hayandra
async def grupo_id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📱 Grupo configurado:\n`{WHATSAPP_GROUP_ID}`",
        parse_mode="Markdown",
    )


@apenas_hayandra
async def receber_tema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = update.message.text.strip()
    if len(tema) < 10:
        return

    await update.message.reply_text("⏳ Pesquisando fontes e escrevendo a newsletter...")
    numero = context.bot_data.get("numero", 1)

    try:
        newsletter = gerar_newsletter(tema, numero)
        context.bot_data["ultima_newsletter"] = newsletter
        context.bot_data["ultimo_tema"] = tema

        await update.message.reply_text(
            f"✅ *Newsletter #{numero} gerada:*\n\n{newsletter}",
            parse_mode="Markdown",
        )

        if "[BUSCAR LINK]" in newsletter:
            await update.message.reply_text(
                "⚠️ Há trechos com `[BUSCAR LINK]`. Revise antes de aprovar ou regenere com tema mais específico.",
                parse_mode="Markdown",
            )

        keyboard = [
            [InlineKeyboardButton("✅ Aprovar e enviar no WhatsApp", callback_data=f"aprovar_{numero}")],
            [
                InlineKeyboardButton("🔄 Regenerar", callback_data="regenerar"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
            ],
        ]
        await update.message.reply_text("O que deseja fazer?", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Erro: {e}")


@apenas_hayandra
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("aprovar_"):
        numero = int(data.split("_")[1])
        newsletter = context.bot_data.get("ultima_newsletter", "")
        await query.edit_message_text("📤 Enviando no grupo do WhatsApp...")

        if enviar_whatsapp(newsletter):
            context.bot_data["numero"] = numero + 1
            await query.message.reply_text(
                f"🎉 *Newsletter #{numero} enviada!*\nPróxima edição: *#{numero + 1}*",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text(
                "❌ Falha ao enviar. Verifique:\n"
                "• Evolution API está online?\n"
                "• WHATSAPP_GROUP_ID está correto?\n"
                "• Instância está conectada?\n\n"
                "Copie o texto acima e envie manualmente se precisar.",
            )

    elif data == "regenerar":
        tema = context.bot_data.get("ultimo_tema", "")
        numero = context.bot_data.get("numero", 1)
        await query.edit_message_text("🔄 Gerando nova versão...")
        newsletter = gerar_newsletter(tema, numero)
        context.bot_data["ultima_newsletter"] = newsletter
        await query.message.reply_text(f"✅ *Nova versão:*\n\n{newsletter}", parse_mode="Markdown")
        keyboard = [
            [InlineKeyboardButton("✅ Aprovar e enviar no WhatsApp", callback_data=f"aprovar_{numero}")],
            [InlineKeyboardButton("🔄 Regenerar", callback_data="regenerar"),
             InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
        ]
        await query.message.reply_text("O que deseja fazer?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "cancelar":
        await query.edit_message_text("❌ Cancelado.")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("numero", numero_cmd))
    app.add_handler(CommandHandler("setnumero", set_numero))
    app.add_handler(CommandHandler("grupoid", grupo_id_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tema))
    logger.info("Bot iniciado.")
    app.run_polling()


if __name__ == "__main__":
    main()
