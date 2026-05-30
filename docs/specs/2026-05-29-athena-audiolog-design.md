# ATHENA — Audiolog Skill Design
**Data:** 2026-05-29  
**Projeto:** Tropico Solar  
**Autor:** Vinicius Abdalla  

---

## Visão Geral

ATHENA é uma skill para Claude Code (e futuramente Codex) que processa áudios de sessões de trabalho — conversas com clientes, suporte técnico, negociações, visitas de campo e brainstorms — transformando-os em transcrições organizadas, análise consultiva e tarefas estruturadas enviadas ao Google Tasks.

ATHENA age como consultora pessoal de negócios: direta, honesta, técnica quando necessário, sempre buscando o menor esforço para o usuário com o resultado mais profissional possível.

---

## Arquitetura

### Camadas

```
SKILL  (/athena)
~/.claude/skills/athena/SKILL.md
~/.agents/skills/athena/SKILL.md  (Codex)
       │
       ▼
PIPELINE PYTHON
E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py
       │
       ▼
SESSÃO (pasta gerada)
E:\OneDrive\01 - AUDIOLOGS\2026\05-MAIO\29\01-NOME_PROJETO\
```

### Pipeline — 4 Estágios

```
ESTÁGIO 1 — TRANSCREVER
  Input:  .ogg e .m4a soltos na raiz de AUDIOLOGS/
  Output: audios/ (arquivos movidos) + transcricao.md
  Engine: Whisper local (openai-whisper, modelo medium, pt)

ESTÁGIO 2 — ANALISAR
  Input:  transcricao.md
  Output: resumo.md (análise ATHENA completa)
  Engine: Claude (via skill)

ESTÁGIO 3 — REVISAR
  Input:  resumo.md → tasks extraídas
  Output: tasks.json (todas, com status pendente/descartada)
  Ação:   Claude apresenta lista, usuário aprova/descarta

ESTÁGIO 4 — ENVIAR
  Input:  tasks.json (apenas aprovadas)
  Output: Tasks criadas no Google Tasks via API
  Engine: google-api-python-client (OAuth2)
```

---

## Estrutura de Pastas

```
E:\OneDrive\01 - AUDIOLOGS\
├── _tools\
│   ├── athena.py              ← pipeline principal
│   ├── credentials.json       ← OAuth2 Google (não commitar)
│   ├── token.json             ← token salvo após 1ª auth
│   └── requirements.txt
│
├── docs\
│   └── superpowers\specs\     ← este arquivo
│
├── 2026\
│   └── 05-MAIO\
│       └── 29\
│           └── 01-NEGOCIACAO_JOAO\
│               ├── audios\
│               │   ├── WhatsApp Ptt 2026-05-29 at 15.03.12.ogg
│               │   └── ...
│               ├── transcricao.md     ← checkpoint estágio 1
│               ├── resumo.md          ← checkpoint estágio 2
│               ├── tasks.json         ← cards ATHENA
│               └── CHANGELOG.md       ← revisões futuras
```

### Nomenclatura de Pasta

Formato: `NN-NOME_PROJETO` onde `NN` é sequencial por dia (01, 02, 03...).  
O nome do projeto é inferido pelo Claude a partir do conteúdo da transcrição, ou informado pelo usuário.

---

## Comportamento do Skill

### Invocação

```
/athena
```

Claude executa:

**Cenário A — Arquivos novos na raiz:**
1. Varre `AUDIOLOGS/` por `.ogg` e `.m4a` soltos na raiz
2. Infere o nome do projeto a partir dos primeiros 30s de transcrição (proper nouns, contexto), confirma com o usuário
3. Conta pastas existentes no dia atual para determinar `NN` (ex: se já há `01-X` e `02-Y`, a nova é `03-Z`)
4. Cria a pasta da sessão
5. Executa os 4 estágios

**Cenário B — Revisita (sem arquivos novos na raiz):**
1. Nenhum áudio solto encontrado
2. Claude lista as sessões mais recentes e pergunta qual revisitar
3. Abre o `resumo.md` + `tasks.json` da sessão escolhida
4. Permite editar tasks, reativar descartadas, adicionar observações
5. Registra mudanças no `CHANGELOG.md` com data e descrição das alterações

### Resumo ATHENA (resumo.md)

Estrutura fixa gerada no estágio 2:

```markdown
# ATHENA — [DATA] [NOME_PROJETO]

## Tipo de Sessão
[cliente / suporte-equatorial / suporte-inversor / distribuidora / brainstorm / outro]

## Participantes Detectados
[lista de pessoas/entidades mencionadas]

## Resumo Executivo
[2-3 parágrafos: o que aconteceu, o que está em jogo]

## Situação Atual
[estado atual do projeto/negociação/problema]

## Pontos de Atenção
[riscos, pendências, oportunidades — formato lista]

## Análise Técnica
[quando aplicável: dimensionamento, normas, especificações]

## Como Proceder
[caminho recomendado — honesto, simples, menor esforço]

## Comunicações Sugeridas
### Para [PESSOA/ENTIDADE]
> [mensagem pronta para copiar — WhatsApp/email]

## Tarefas Identificadas
[lista preliminar — detalhada nos cards]
```

---

## Schema ATHENA Cards

Baseado no padrão oficial ATHENA:

```json
{
  "session_id": "2026-05-29_01-NEGOCIACAO_JOAO",
  "tasks": [
    {
      "id": 1,
      "status": "pendente",
      "titulo": "🔴💰 JOÃO VITOR - Enviar proposta revisada",
      "prioridade": 1,
      "prioridade_emoji": "🔴",
      "prioridade_label": "Alta (Urgente)",
      "categoria": 1,
      "categoria_emoji": "💰",
      "categoria_label": "Vendas",
      "o_que_precisa": "Enviar a proposta com o novo dimensionamento de 5kWp.",
      "responsavel": "EU",
      "mensagem_sugerida": "João, segue a proposta atualizada conforme combinamos...",
      "whatsapp": "5511999999999",
      "observacoes": [
        "Incluir garantia do inversor",
        "Mencionar prazo de instalação"
      ],
      "data": "2026-05-30"
    }
  ]
}
```

### Tabela de Prioridades

| Código | Emoji | Nível |
|--------|-------|-------|
| 1 | 🔴 | Alta (Urgente) |
| 2 | 🟠 | Média-Alta (Importante) |
| 3 | 🟡 | Média-Baixa (Pode aguardar) |
| 4 | 🟢 | Baixa (Sem pressa) |

### Tabela de Categorias

| Código | Emoji | Categoria |
|--------|-------|-----------|
| 1 | 💰 | Vendas |
| 2 | 🗒️ | Escritório |
| 3 | 👷 | Obras |
| 4 | 😎 | Pessoal |
| 5 | 📋 | Pós-venda |

---

## Estágio de Revisão

Após estágio 2, Claude apresenta:

```
📋 ATHENA — TASKS GERADAS
Sessão: 2026-05-29 / NEGOCIAÇÃO JOÃO VITOR

  1. 🔴💰 JOÃO VITOR - Enviar proposta revisada         → prazo: amanhã
  2. 🟠🗒️ EU - Calcular novo dimensionamento            → prazo: hoje
  3. 🟡👷 EU - Agendar visita técnica                   → prazo: semana que vem
  4. 🟢📋 JOÃO VITOR - Confirmar pagamento entrada      → sem prazo

Quais enviar para o Google Tasks?
("todas", "nenhuma", ou números: "1 3 4")
```

Tasks rejeitadas são salvas no `tasks.json` com `"status": "descartada"` — recuperáveis depois.

---

## Google Tasks — Integração

### Setup (uma vez)

1. Criar projeto no Google Cloud Console
2. Ativar Google Tasks API
3. Criar credenciais OAuth2 → baixar `credentials.json`
4. Colocar em `AUDIOLOGS/_tools/credentials.json`
5. Na primeira execução: browser abre para autorizar → `token.json` salvo automaticamente

### Campos mapeados para Google Tasks

| Campo ATHENA | Campo Google Tasks |
|---|---|
| titulo | title |
| data | due (RFC 3339) |
| o_que_precisa + mensagem_sugerida + observacoes | notes |

---

## CHANGELOG — Revisitas

Toda vez que `/athena` é invocado em uma sessão **já existente**, o CHANGELOG.md recebe uma entrada:

```markdown
## 2026-06-01 — Revisão por Vinicius
- Prazo da task 1 atualizado para 2026-06-05
- Task 3 reativada (estava descartada)
- Adicionada observação: cliente pediu desconto de 10%
```

---

## Dependências Python

```
openai-whisper
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

---

## Compatibilidade Codex

O mesmo `SKILL.md` é copiado para `~/.agents/skills/athena/` com ajuste mínimo nas referências de ferramentas (Bash → shell equivalente do Codex). O `athena.py` roda igual — é Python puro.

---

## Fora de Escopo (v1)

- Notificações automáticas por WhatsApp (pode ser v2 via Twilio/Z-API)
- Interface gráfica
- Processamento de vídeo
- Integração com Notion/Trello
