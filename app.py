# -*- coding: utf-8 -*-
import os
import re
import json
from flask import Flask, render_template, request, jsonify
from io import BytesIO
from pypdf import PdfReader
from dotenv import load_dotenv

# OpenAI (SDK novo)
from openai import OpenAI

# Carrega variáveis de ambiente (ex.: OPENAI_API_KEY, OPENAI_MODEL)
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# -----------------------------
# Utilitários
# -----------------------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages)

def extract_text_from_upload(upload) -> str:
    filename = (upload.filename or "").lower()
    data = upload.read()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(data)
    # tenta UTF-8 e fallback Latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return ""  # se nada funcionar

# -----------------------------
# OpenAI: classificação + resposta
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # pedido: usar 3.5

# Termos e pistas: colocamos no prompt (NÃO em código lógico)
CLASS_RULES = r"""
Você é um assistente que classifica e-mails RECEBIDOS (pt-BR) em:
- "Produtivo": requer ação/resposta relacionada ao trabalho/negócio/operacional.
- "Improdutivo": saudações, mensagens sociais, divulgação, sem ação de trabalho.

USE AS PISTAS ABAIXO COMO GUIA (não são listas exaustivas):
- Exemplos de temas de TRABALHO (sinais de produtivo): status, andamento, suporte, erro, falha, bug, pendente, prazo, protocolo, anexo, documento, comprovante, fatura, boleto, agendamento, cancelamento, reembolso, cadastro, senha, acesso, liberação, homologação, produção, financeiro, pagamento, estorno, chamado, ticket, retorno, resposta, confirmar, verificar, verificação, atender, resolver, contrato, nota fiscal, NF, cobrança, fornecedor, cliente, proposta, orçamento, infraestrutura, servidor, API, deploy, SLA, faturamento, auditoria.
- Exemplos de NÃO TRABALHO/IMPRODUTIVO: "feliz natal", "feliz ano novo", "boas festas", "parabéns", "felicidades", "bom dia/boa tarde/boa noite" sem pedido concreto, agradecimentos genéricos, "newsletter", "divulgação", "promoção".

RETORNE SOMENTE JSON de uma única linha:
{
  "categoria": "Produtivo" | "Improdutivo",
  "resposta": "string"
}

REGRAS DE RESPOSTA (use exatamente estes textos):
- Se "Improdutivo":
  "resposta": "Obrigado pelo contato! Vimos sua mensagem. Responderemos assim que possível."
- Se "Produtivo":
  "resposta": "Obrigado pelo contato! Vimos sua demanda e vamos redirecioná-la para alguém responsável imediatamente."
- Não inclua comentários fora do JSON. Não use markdown. Retorne SOMENTE o JSON.
"""

def openai_classify_and_reply(email_text: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY ausente nas variáveis de ambiente.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Monta mensagens
    system_msg = CLASS_RULES
    user_msg = f"Email recebido (pt-BR):\n---\n{email_text}\n---"

    # Chamada ao Chat Completions (3.5)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        # Nota: JSON mode oficial nem sempre está disponível no 3.5,
        # então preferimos instrução + parse robusto abaixo.
    )
    content = resp.choices[0].message.content.strip()

    # Tenta parse direto; se vier com texto extra, extrai o primeiro {...}
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not m:
            # Fallback mínimo
            return {"categoria": "Improdutivo", "resposta": "Not OK"}
        try:
            return json.loads(m.group(0))
        except Exception:
            return {"categoria": "Improdutivo", "resposta": "Not OK"}

# -----------------------------
# Orquestração
# -----------------------------
def classify_and_respond(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"erro": "Nenhum texto foi fornecido."}

    data = openai_classify_and_reply(text)
    categoria = data.get("categoria", "Improdutivo")
    resposta = data.get("resposta", "Not OK")
    return {
        "categoria": categoria,
        "resposta": resposta,
        "origem": "openai"
    }

# -----------------------------
# Rotas
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    try:
        return render_template("index.html")
    except Exception:
        return """
        <html><body style="font-family: sans-serif;">
            <h3>Classificador de E-mails (OpenAI gpt-3.5)</h3>
            <form method="POST" action="/process" enctype="multipart/form-data">
                <textarea name="email_text" rows="8" cols="80" placeholder="Cole o texto do e-mail aqui"></textarea><br/>
                <input type="file" name="email_file" />
                <button type="submit">Processar</button>
            </form>
        </body></html>
        """

@app.route("/process", methods=["POST"])
def process():
    email_text = request.form.get("email_text", "").strip()

    if not email_text and "email_file" in request.files:
        f = request.files["email_file"]
        if f and f.filename:
            try:
                email_text = extract_text_from_upload(f)
            except Exception as e:
                return jsonify({"erro": f"Falha ao ler arquivo: {e}"}), 400

    result = classify_and_respond(email_text)
    if "erro" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
