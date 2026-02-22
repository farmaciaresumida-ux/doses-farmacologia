"""
Doses de Farmacologia — Bot Telegram + Agente Newsletter
Farmácia Resumida | Hayandra Costa

Fluxo:
1. Você envia o tema/caso para o bot no Telegram
2. O agente pesquisa fontes clínicas reais
3. Claude escreve a newsletter no seu estilo
4. Bot te envia o texto formatado para revisão
5. Você copia e agenda no Reportana
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
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEU_TELEGRAM_ID = int(os.environ["SEU_TELEGRAM_ID"])  # só você pode usar o bot

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
1. NUNCA invente links. Se não tiver link real, escreva [BUSCAR LINK] para a Hayandra completar
2. Toda afirmação clínica deve ter embasamento identificável (mecanismo, estudo, diretriz)
3. Mantenha o tom crítico — questione prescrições, separe crença de evidência
4. Use *negrito* e _itálico_ na formatação do WhatsApp
5. Seja conciso: o raciocínio deve ser denso, não longo
6. A pergunta final deve provocar reflexão clínica real, não ser genérica"""


# ─────────────────────────────────────────
# PESQUISA DE FONTES (PubMed)
# ─────────────────────────────────────────
def buscar_pubmed(tema: str, max_results: int = 3) -> list[dict]:
    """Busca artigos relevantes no PubMed para embasar a newsletter."""
    try:
        # Busca IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": tema,
            "retmax": max_results,
            "sort": "relevance",
            "retmode": "json",
        }
        r = requests.get(search_url, params=params, timeout=10)
        ids = r.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # Busca detalhes
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params2 = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        r2 = requests.get(summary_url, params=params2, timeout=10)
        result = r2.json().get("result", {})

        artigos = []
        for uid in ids:
            doc = result.get(uid, {})
            titulo = doc.get("title", "")
            journal = doc.get("fulljournalname", "")
            ano = doc.get("pubdate", "")[:4]
            link = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
            if titulo:
                artigos.append(
                    {"titulo": titulo, "journal": journal, "ano": ano, "link": link}
                )
        return artigos

    except Exception as e:
        logger.warning(f"Erro PubMed: {e}")
        return []


# ─────────────────────────────────────────
# GERAÇÃO DA NEWSLETTER
# ─────────────────────────────────────────
def gerar_newsletter(tema: str, numero: int) -> str:
    """Chama Claude para gerar a newsletter com base no tema."""

    # Busca fontes reais no PubMed
    artigos = buscar_pubmed(tema)
    contexto_artigos = ""
    if artigos:
        contexto_artigos = "\n\nARTIGOS ENCONTRADOS NO PUBMED (use como referência):\n"
        for a in artigos:
            contexto_artigos += f"- {a['titulo']} ({a['journal']}, {a['ano']}) → {a['link']}\n"

    prompt = f"""Crie a newsletter número {numero} sobre o seguinte tema:

TEMA: {tema}
{contexto_artigos}

Identifique automaticamente se é um caso clínico ou notícia/atualidade e use a estrutura correspondente.
Lembre: se não tiver link real para alguma seção, escreva [BUSCAR LINK]."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


# ─────────────────────────────────────────
# HANDLERS DO BOT
# ─────────────────────────────────────────
def apenas_hayandra(func):
    """Decorator: só a Hayandra pode usar o bot."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != SEU_TELEGRAM_ID:
            await update.message.reply_text("⛔ Acesso restrito.")
            return
        return await func(update, context)
    return wrapper


@apenas_hayandra
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💊 *Doses de Farmacologia — Bot Ativo*\n\n"
        "Me mande o tema do dia assim:\n\n"
        "📌 Para caso clínico:\n"
        "`caso: amoxicilina + ciprofloxacino em ITU persistente, homem 52 anos`\n\n"
        "📌 Para notícia:\n"
        "`notícia: rivotril saiu do mercado`\n\n"
        "Use /numero para ver/definir o número da edição atual.",
        parse_mode="Markdown",
    )


@apenas_hayandra
async def numero_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numero_atual = context.bot_data.get("numero", 1)
    await update.message.reply_text(
        f"📌 Próxima edição: *#{numero_atual}*\n"
        f"Para alterar: `/setnumero 15`",
        parse_mode="Markdown",
    )


@apenas_hayandra
async def set_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.args[0])
        context.bot_data["numero"] = n
        await update.message.reply_text(f"✅ Número atualizado para *#{n}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("Use: `/setnumero 15`", parse_mode="Markdown")


@apenas_hayandra
async def receber_tema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = update.message.text.strip()

    # Ignora mensagens muito curtas
    if len(tema) < 10:
        return

    await update.message.reply_text("⏳ Pesquisando fontes e escrevendo a newsletter...")

    numero = context.bot_data.get("numero", 1)

    try:
        newsletter = gerar_newsletter(tema, numero)

        # Envia a newsletter
        await update.message.reply_text(
            f"✅ *Newsletter #{numero} gerada:*\n\n{newsletter}",
            parse_mode="Markdown",
        )

        # Botões de ação
        keyboard = [
            [
                InlineKeyboardButton("✅ Aprovada — avançar número", callback_data=f"aprovar_{numero}"),
                InlineKeyboardButton("🔄 Gerar novamente", callback_data=f"regenerar_{tema}"),
            ]
        ]
        await update.message.reply_text(
            "O que deseja fazer?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        logger.error(f"Erro ao gerar newsletter: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")


@apenas_hayandra
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("aprovar_"):
        numero = int(data.split("_")[1])
        context.bot_data["numero"] = numero + 1
        await query.edit_message_text(
            f"✅ Edição #{numero} aprovada!\n"
            f"Próxima edição será *#{numero + 1}*\n\n"
            f"📋 Copie o texto acima e agende no Reportana.",
            parse_mode="Markdown",
        )

    elif data.startswith("regenerar_"):
        tema = data.replace("regenerar_", "")
        numero = context.bot_data.get("numero", 1)
        await query.edit_message_text("🔄 Gerando nova versão...")
        newsletter = gerar_newsletter(tema, numero)
        await query.message.reply_text(newsletter, parse_mode="Markdown")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("numero", numero_cmd))
    app.add_handler(CommandHandler("setnumero", set_numero))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tema))

    logger.info("Bot iniciado.")
    app.run_polling()


if __name__ == "__main__":
    main()
