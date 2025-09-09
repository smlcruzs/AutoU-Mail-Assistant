# AutoU — Classificador de Emails (Flask)

Protótipo simples que **classifica e-mails** como **Produtivo** ou **Improdutivo** e **sugere uma resposta automática**.
- **Stack:** Python (Flask) + (opcional) OpenAI para IA, com **fallback heurístico** local.
- **Upload** de `.txt`/`.pdf` **ou** colar texto direto.
- **Interface** mínima com Tailwind (CDN) e UX rápida.

> Este projeto é um candidato a solução para o case prático. Ele roda localmente e pode ser publicado em ambientes gratuitos como Render.com.

## Demo local

```bash
# 1) Clonar e entrar na pasta
# git clone <seu-fork-ou-repo>
cd autou-email-assistant

# 2) Criar venv e instalar dependências
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) (Opcional) Configurar OpenAI
cp .env.example .env
# edite .env e informe OPENAI_API_KEY
# habilite ENABLE_OPENAI=1 se quiser usar o modelo (senão será heurístico)

# 4) Rodar
python app.py
# abrir http://localhost:8000
```

## Variáveis de ambiente (.env)

```
OPENAI_API_KEY=sk-...
ENABLE_OPENAI=0
OPENAI_MODEL=gpt-4o-mini
PORT=8000
```

- Se `ENABLE_OPENAI=0` **ou** não houver `OPENAI_API_KEY`, o app usa **heurísticas locais** para classificar e responder.
- Se `ENABLE_OPENAI=1` e a chave existir, o app usa a API da OpenAI (com fallback para heurística se falhar).

## Deploy (Render.com)

1. Faça push para um repositório público no GitHub.
2. Crie um **Web Service** no Render:
   - Runtime: **Python 3.11**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Defina `OPENAI_API_KEY` (opcional) e `ENABLE_OPENAI` como variáveis de ambiente.
3. A URL pública ficará disponível ao término do deploy.

> Também é possível publicar no Railway/Zeet/etc. via `Procfile`.

## Como funciona

- **Pré-processamento (NLP):** normalização simples, remoção de stopwords PT e contagem de palavras-chave.
- **Classificação:**
  - **Heurística:** palavras-chave + sinais de pergunta + densidade de tokens.
  - **IA (opcional):** prompt orientado para JSON (`categoria`, `justificativa`, `resposta`) usando OpenAI.
- **Geração de resposta:**
  - **IA (opcional)** sugere resposta sob medida.
  - **Fallback:** templates específicos por tema (status, anexo, acesso/senha) ou resposta genérica educada.
- **PDF:** extração de texto usando `pypdf`.

## Estrutura

```
autou-email-assistant/
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── templates/
│   ├── base.html
│   └── index.html
├── sample_emails/
│   ├── produtivo_status.txt
│   └── improdutivo_felicidades.txt
└── README.md
```

## Teste rápido (sem OpenAI)

- Em **sample_emails** há dois exemplos. Você pode colar o conteúdo ou anexar os arquivos.
- Esperado:
  - `produtivo_status.txt` → **Produtivo** com resposta pedindo/confirmando protocolo e prazo.
  - `improdutivo_felicidades.txt` → **Improdutivo** com resposta cordial.

## Observações técnicas

- O código tenta usar o SDK **novo** da OpenAI (`from openai import OpenAI`) e faz **fallback** para o legado se necessário.
- A saída do endpoint `/process` é **JSON**, o front consome via `fetch` e atualiza a UI.
- Limite de upload: **2MB** (configurável).
- `PORT` padrão: **8000**.

## Ideias de evolução (futuro)

- Ajuste fino com exemplos reais (few-shot) e cache de respostas frequentes.
- Regras por cliente/time, dicionário de entidades, e templates personalizados por categoria.
- Fila assíncrona, logs e métricas; suporte a IMAP/Gmail API para ingestão automática.
- RAG com base interna para respostas mais específicas.
```

## Licença

MIT
