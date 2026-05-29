# ATHENA — Contexto e Memória

## Sobre o Usuário

**Nome:** Vinicius Abdalla  
**Email:** viniabdalla00@gmail.com  
**Empresa:** Tropico Solar  
**Função:** Sócio / Engenheiro / Gestor de projetos e vendas  

---

## Sobre a Tropico Solar

Empresa de energia solar fotovoltaica. Atua em vendas, engenharia de projetos, instalação e pós-venda de sistemas solares on-grid e off-grid.

**Áreas de operação:**
- Dimensionamento e engenharia de sistemas fotovoltaicos
- Negociação com clientes (residencial, comercial, rural)
- Relacionamento com concessionária Equatorial
- Compra com distribuidoras de equipamentos
- Suporte técnico de inversores e módulos

---

## Ecossistema de Ferramentas

| Ferramenta | Uso |
|---|---|
| **Google Tasks** | Gestão de tarefas pessoais — ATHENA envia cards aqui |
| **Kommo CRM** | CRM de vendas — pipeline de clientes |
| **Make (Integromat)** | Automações (fluxos legados) |
| **ARTEMIS** | Sistema interno de geração de faturas e contratos |
| **Claude Code** | Desenvolvimento e automações com IA |
| **Codex** | Agente de código paralelo |
| **OneDrive** | Armazenamento de arquivos e projetos |

---

## Sistema de Cards ATHENA

### Prioridades

| Código | Emoji | Nível | Critério |
|--------|-------|-------|----------|
| 1 | 🔴 | Alta (Urgente) | Precisa hoje ou amanhã |
| 2 | 🟠 | Média-Alta (Importante) | Essa semana |
| 3 | 🟡 | Média-Baixa (Pode aguardar) | Próximas 2 semanas |
| 4 | 🟢 | Baixa (Sem pressa) | Quando der |

### Categorias

| Código | Emoji | Categoria | Exemplos |
|--------|-------|-----------|---------|
| 1 | 💰 | Vendas | Proposta, negociação, follow-up cliente |
| 2 | 🗒️ | Escritório | Documentação, fatura, contrato, burocracia |
| 3 | 👷 | Obras | Instalação, vistoria, comissionamento |
| 4 | 😎 | Pessoal | Tarefas pessoais do Vinicius |
| 5 | 📋 | Pós-venda | Suporte, garantia, manutenção |

### Formato do Título
```
[EMOJI_PRIORIDADE][EMOJI_CATEGORIA] [RESPONSAVEL] - [descrição curta]
```
Exemplo: `🔴💰 JOÃO VITOR - Enviar proposta revisada`

---

## Entidades Recorrentes

### Concessionária
- **Equatorial** — distribuidora de energia. Contato frequente para: vistoria de rede, aprovação de projetos, ligação nova, troca de medidor bidirecional, protocolos.

### Fornecedores / Suporte
- Suporte de inversores (Growatt, Deye, Fronius, etc.)
- Distribuidoras de equipamentos solares
- Engenheiros parceiros

### Clientes
- Pessoas físicas e jurídicas — nomes inferidos da transcrição
- Responsável padrão pelo follow-up: **Vinicius (EU)**

---

## Contexto Técnico Solar

### Normas aplicáveis
- **ABNT NBR 16690** — Instalações elétricas de sistemas fotovoltaicos
- **ANEEL RN 482/2012** — Marco regulatório da microgeração distribuída
- **ANEEL RN 687/2015** — Atualização das condições de acesso
- **ANEEL RN 1000/2021** — Regulamentação vigente de micro e minigeração

### Dimensionamento típico
- String box / proteções CC e CA
- Inversor string vs. microinversor
- Fator de dimensionamento: 0.75 a 0.85
- Orientação ideal: norte, inclinação ~latitude local
- Perdas: cabos, temperatura, sujeira (~20% total)

### Documentação de projeto
- Memorial descritivo
- Diagrama unifilar
- ART (Anotação de Responsabilidade Técnica)
- Projeto elétrico e estrutural

---

## Arquivos e Caminhos

| Item | Caminho |
|---|---|
| Base de audiologs | `E:\OneDrive\01 - AUDIOLOGS` |
| Script principal | `E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py` |
| Credenciais Google | `E:\OneDrive\01 - AUDIOLOGS\_tools\credentials.json` |
| Token Google | `E:\OneDrive\01 - AUDIOLOGS\_tools\token.json` |
| Groq API key | `E:\OneDrive\01 - AUDIOLOGS\_tools\groq_key.txt` |
| Skill Claude | `C:\Users\viniabdalla\.claude\skills\athena\SKILL.md` |
| Skill Codex | `C:\Users\viniabdalla\.agents\skills\athena\SKILL.md` |
| Repositório | https://github.com/viniabdalla/skill_athena |

---

## Preferências de Comunicação

- **Idioma:** Português brasileiro (pt-BR)
- **Tom:** Direto, sem enrolação, honesto sobre riscos
- **Mensagens sugeridas:** WhatsApp — informal mas profissional, máximo 3 parágrafos curtos
- **Análise:** Objetiva, foco em ação, menor esforço possível para Vinicius
- **Prazos:** Sempre sugerir data concreta quando possível

---

## Histórico de Sessões

> Atualizado automaticamente a cada nova sessão processada.
> Formato: DATA | TIPO | NOME | TASKS_GERADAS | TASKS_ENVIADAS

| Data | Tipo | Sessão | Tasks |
|------|------|--------|-------|
| — | — | Nenhuma sessão processada ainda | — |
