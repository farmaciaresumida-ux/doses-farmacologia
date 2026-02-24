from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Literal

NewsletterKind = Literal["caso_clinico", "noticia"]


@dataclass
class Draft:
    draft_id: str
    date_ref: date
    topics: List[str]
    kind: NewsletterKind
    content: str
    approved: bool = False


class LLMClient:
    """Stub de LLM. Troque por integração real."""

    def generate_topic_suggestions(self, business_context: str) -> List[str]:
        return [
            f"Caso clínico com erro de dose/polifarmácia em {business_context}",
            "Notícia da semana com impacto real na prescrição",
            "Regra prática de farmacologia clínica para decisão rápida",
        ]


class WhatsAppClient:
    """Stub de WhatsApp. Troque por API oficial (Twilio/BSP/Meta)."""

    def send_message(self, to: str, text: str) -> None:
        print(f"[WHATSAPP -> {to}]\n{text}\n")


@dataclass
class NewsletterAgent:
    owner_number: str
    group_ids: List[str]
    business_context: str
    llm: LLMClient = field(default_factory=LLMClient)
    whatsapp: WhatsAppClient = field(default_factory=WhatsAppClient)
    drafts: Dict[str, Draft] = field(default_factory=dict)

    def daily_scheduler(self, when: date | None = None) -> Draft:
        when = when or date.today()
        topics = self.llm.generate_topic_suggestions(self.business_context)
        kind: NewsletterKind = "caso_clinico" if when.toordinal() % 2 == 0 else "noticia"
        content = self._build_newsletter(kind=kind, issue_number=when.isocalendar().week, topics=topics)

        draft_id = f"draft-{when.isoformat()}"
        draft = Draft(
            draft_id=draft_id,
            date_ref=when,
            topics=topics,
            kind=kind,
            content=content,
        )
        self.drafts[draft_id] = draft

        self.send_for_approval(draft)
        return draft

    def send_for_approval(self, draft: Draft) -> None:
        msg = (
            f"Sugestões de temas do dia:\n{chr(10).join(f'- {t}' for t in draft.topics)}\n\n"
            f"Formato escolhido hoje: {draft.kind}\n\n"
            f"Newsletter pronta para aprovação:\n\n{draft.content}\n\n"
            f"Para aprovar: POST /approval {{'draft_id':'{draft.draft_id}','approved':true}}"
        )
        self.whatsapp.send_message(self.owner_number, msg)

    def set_approval(self, draft_id: str, approved: bool) -> Draft:
        if draft_id not in self.drafts:
            raise ValueError("Draft não encontrado")

        draft = self.drafts[draft_id]
        draft.approved = approved

        if approved:
            self.dispatch_to_groups(draft)
        else:
            self.whatsapp.send_message(
                self.owner_number,
                f"Draft {draft_id} reprovado. Posso gerar nova versão mantendo o mesmo formato.",
            )

        return draft

    def dispatch_to_groups(self, draft: Draft) -> None:
        for group_id in self.group_ids:
            self.whatsapp.send_message(group_id, draft.content)

        self.whatsapp.send_message(
            self.owner_number,
            f"Disparo concluído para {len(self.group_ids)} grupo(s). Draft: {draft.draft_id}",
        )

    def _build_newsletter(self, kind: NewsletterKind, issue_number: int, topics: List[str]) -> str:
        if kind == "caso_clinico":
            return self._model_caso_clinico(issue_number=issue_number, topics=topics)
        return self._model_noticia(issue_number=issue_number, topics=topics)

    def _model_caso_clinico(self, issue_number: int, topics: List[str]) -> str:
        return f"""*💊 #{issue_number} Doses de Farmacologia*

Aqui, prescrições comuns são desmontadas com farmacologia clínica.
Achismo não entra.

*🩺 O caso*

Amoxicilina/Clavulanato 875/125 mg — 12/12h
Ciprofloxacino 500 mg — 12/12h

Homem, 52 anos.
ITU “que não melhora”.

*🧠 O raciocínio*

Empilhar dois antibióticos de amplo espectro pode fazer sentido em infecções graves.
Em ITU persistente sem urocultura, isso se parece mais com escalada cega do que decisão racional.

O custo invisível aparece rápido:
amoxi/clav + ciprofloxacino = diarreia quase certa.
E um detalhe ignorado com frequência: ciprofloxacino em homens >50 anos aumenta o risco de tendinopatia — especialmente se houver corticoide associado.

Mais antibiótico não corrige raciocínio frágil.

*📌 A regra*

Quando a infecção não melhora, adicionar antibiótico costuma ser o sintoma — não a solução.

*Pílulas extras 💊*

📰 Notícia que me fez parar:
{topics[1]}
🔗https://acesse.one/fXGic

📚 O que me deixou 1% mais crítica essa semana:
ITU + resistência: o que fazer quando nada funciona
🔗https://www.nature.com/articles/s41585-024-00877-9

📖 O que estou estudando:
{topics[2]}

💬 E você, qual prescrição te fez parar essa semana?

P.S.
Se esse tipo de raciocínio clínico faz sentido pra você, o livro Antibióticos em Casos Clínicos existe exatamente pra isso:
treinar o olhar, cortar o achismo e decidir melhor diante de casos reais.
🔗 https://hayandracosta.com.br/vendas-livro-antibioticos/

_Farmacologia clínica é o antídoto contra o achismo._"""

    def _model_noticia(self, issue_number: int, topics: List[str]) -> str:
        return f"""💊 *#{issue_number} Doses de Farmacologia*
Aqui, prescrições comuns são desmontadas com farmacologia clínica.
Achismo não entra.

🩺*“Rivotril saiu do mercado.”*
A notícia causou alarme — mas não interrompeu tratamentos.

🧠 *O raciocínio*

O que saiu do mercado foi a marca (Roche-Rivotril), por decisão comercial.
O clonazepam continua disponível no Brasil em versões genéricas e similares.

*Na prática:*
• comprimidos 0,5 mg e 2 mg seguem sendo comercializados
• gotas continuam disponíveis
• o efeito farmacológico é o mesmo, independentemente da marca

A confusão começa quando marca vira sinônimo de tratamento.

_O impacto real foi o fim da apresentação sublingual._

*E aqui vale o ajuste técnico:* 
clonazepam é lipofílico → não tem absorção sublingual significativamente superior à via oral.
O “efeito ultra-rápido”? Em grande parte, placebo.

*As gotas, por outro lado, oferecem vantagens reais:*
• ajuste de dose mais preciso
• titulação mais segura (especialmente no desmame)
• menos risco de uso impulsivo em crises

📌 *A regra*

Quando a marca some, mas o fármaco permanece,
o problema raramente é farmacológico.

Farmacologia clínica é o antídoto contra o achismo.

💊 *Pílulas extras*

📰 Notícia que dominou a semana
{topics[1]}
🔗 https://site.cff.org.br/noticia/Noticias-gerais/29/09/2025/rivotril-some-das-farmacias-brasileiras-nas-versoes-em-gotas-e-sublingual

📚 Para pensar melhor
Uso prolongado de benzodiazepínicos, dependência e desprescrição
🔗 https://www.nature.com/articles/s41572-021-00311-5

📖 O que estou revisitando
{topics[0]}
🔗 https://www.ncbi.nlm.nih.gov/books/NBK556010/

💬 E você?
Como tem orientado seus pacientes nessa transição?

P.S.
Se você quer treinar esse tipo de raciocínio — separar marca, percepção e efeito clínico real — os estudos por casos clínicos existem exatamente pra isso.
🔗https://hotmart.com/pt-br/club/farmacia-resumida."""
