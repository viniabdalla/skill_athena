# ATHENA Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build ATHENA — skill para Claude Code que transcreve áudios de sessões, gera análise consultiva e envia task cards para o Google Tasks via API direta.

**Architecture:** `athena.py` (Python) lida com I/O de arquivos, transcrição via Whisper e chamadas à Google Tasks API. `SKILL.md` instrui o Claude a orquestrar os 4 estágios e fazer a análise de negócio. Comunicação entre os dois via sistema de arquivos (`transcricao.md`, `resumo.md`, `tasks.json`).

**Tech Stack:** Python 3.12, openai-whisper, google-api-python-client, google-auth-oauthlib, Claude Code skill system

---

## File Map

```
E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\
├── SKILL.md                  ← instrução completa para o Claude
├── athena.py                 ← pipeline: scan / transcribe / push / list
├── setup_google.py           ← setup OAuth2 (executa uma vez)
├── requirements.txt
└── tests\
    ├── conftest.py           ← sys.path fix
    ├── test_session.py       ← testa create_session_folder, find_loose_audios
    ├── test_transcribe.py    ← testa transcribe_session (mock whisper)
    └── test_push.py          ← testa push_tasks (mock google API)
```

**Deployed locations (após Task 8):**
- `SKILL.md` → `C:\Users\viniabdalla\.claude\skills\athena\SKILL.md`
- `athena.py` → `E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py`
- `setup_google.py` → `E:\OneDrive\01 - AUDIOLOGS\_tools\setup_google.py`

---

## Task 1: Project setup

**Files:**
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\requirements.txt`
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\tests\conftest.py`

- [ ] **Step 1: Criar requirements.txt**

```
openai-whisper
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
pytest
```

- [ ] **Step 2: Criar tests/conftest.py**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 3: Instalar dependências**

Run: `pip install openai-whisper google-api-python-client google-auth-httplib2 google-auth-oauthlib pytest`

Expected: `Successfully installed ...` (sem erros)

- [ ] **Step 4: Verificar whisper**

Run: `python -c "import whisper; print(whisper.__version__)"`

Expected: número de versão impresso sem erro

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/conftest.py
git commit -m "feat(athena): project setup and dependencies"
```

---

## Task 2: Session folder logic

**Files:**
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\athena.py` (parcial — só funções de sessão)
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\tests\test_session.py`

- [ ] **Step 1: Escrever testes de sessão**

`tests/test_session.py`:
```python
import pytest
from pathlib import Path
from datetime import datetime
from athena import find_loose_audios, get_next_session_number, create_session_folder


def test_find_loose_audios_returns_only_audio_in_root(tmp_path):
    (tmp_path / "audio.ogg").write_bytes(b"")
    (tmp_path / "audio.m4a").write_bytes(b"")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.ogg").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("text")

    result = find_loose_audios(tmp_path)
    assert len(result) == 2
    assert all(f.parent == tmp_path for f in result)


def test_find_loose_audios_empty_dir(tmp_path):
    assert find_loose_audios(tmp_path) == []


def test_get_next_session_number_no_dir(tmp_path):
    assert get_next_session_number(tmp_path / "nonexistent") == 1


def test_get_next_session_number_with_existing(tmp_path):
    (tmp_path / "01-PROJETO_A").mkdir()
    (tmp_path / "02-PROJETO_B").mkdir()
    (tmp_path / "arquivo.txt").write_text("")  # não conta
    assert get_next_session_number(tmp_path) == 3


def test_create_session_folder_structure(tmp_path):
    dt = datetime(2026, 5, 29)
    session_dir = create_session_folder(tmp_path, "NEGOCIACAO JOAO", dt)

    assert session_dir.exists()
    assert (session_dir / "audios").exists()
    assert session_dir.name == "01-NEGOCIACAO_JOAO"
    assert session_dir.parent.name == "29"
    assert session_dir.parent.parent.name == "05-MAIO"
    assert session_dir.parent.parent.parent.name == "2026"


def test_create_session_folder_sequential(tmp_path):
    dt = datetime(2026, 5, 29)
    s1 = create_session_folder(tmp_path, "REUNIAO_A", dt)
    s2 = create_session_folder(tmp_path, "REUNIAO_B", dt)
    assert s1.name.startswith("01-")
    assert s2.name.startswith("02-")


def test_create_session_folder_slugifies_name(tmp_path):
    dt = datetime(2026, 5, 29)
    session_dir = create_session_folder(tmp_path, "negociação joão & vitor", dt)
    assert " " not in session_dir.name
    assert "&" not in session_dir.name
```

- [ ] **Step 2: Rodar testes — confirmar FAIL**

Run: `cd "E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA" && python -m pytest tests/test_session.py -v`

Expected: `ModuleNotFoundError: No module named 'athena'`

- [ ] **Step 3: Criar athena.py com funções de sessão**

`athena.py`:
```python
#!/usr/bin/env python3
"""ATHENA — pipeline de transcrição e integração Google Tasks."""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MONTH_PT = {
    1: "01-JANEIRO", 2: "02-FEVEREIRO", 3: "03-MARÇO", 4: "04-ABRIL",
    5: "05-MAIO",    6: "06-JUNHO",     7: "07-JULHO", 8: "08-AGOSTO",
    9: "09-SETEMBRO",10: "10-OUTUBRO", 11: "11-NOVEMBRO",12: "12-DEZEMBRO",
}

AUDIO_EXTS = {".ogg", ".m4a", ".mp3", ".wav"}


def find_loose_audios(base_dir: Path) -> list:
    return [
        f for f in base_dir.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    ]


def get_next_session_number(day_dir: Path) -> int:
    if not day_dir.exists():
        return 1
    existing = [
        d for d in day_dir.iterdir()
        if d.is_dir() and re.match(r"^\d{2}-", d.name)
    ]
    return len(existing) + 1


def create_session_folder(base_dir: Path, session_name: str, dt: datetime = None) -> Path:
    if dt is None:
        dt = datetime.now()
    day_dir = base_dir / str(dt.year) / MONTH_PT[dt.month] / f"{dt.day:02d}"
    n = get_next_session_number(day_dir)
    slug = re.sub(r"[^A-Z0-9]", "_", session_name.upper())
    slug = re.sub(r"_+", "_", slug).strip("_")
    session_dir = day_dir / f"{n:02d}-{slug}"
    (session_dir / "audios").mkdir(parents=True, exist_ok=True)
    return session_dir


if __name__ == "__main__":
    pass  # CLI adicionado na Task 5
```

- [ ] **Step 4: Rodar testes — confirmar PASS**

Run: `python -m pytest tests/test_session.py -v`

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add athena.py tests/test_session.py
git commit -m "feat(athena): session folder creation and audio discovery"
```

---

## Task 3: Transcrição — Estágio 1

**Files:**
- Modify: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\athena.py` (adicionar transcribe_session)
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\tests\test_transcribe.py`

- [ ] **Step 1: Escrever testes de transcrição**

`tests/test_transcribe.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from athena import transcribe_session


def test_transcribe_moves_files_and_creates_output(tmp_path):
    session_dir = tmp_path / "01-TEST"
    (session_dir / "audios").mkdir(parents=True)

    audio1 = tmp_path / "audio1.ogg"
    audio2 = tmp_path / "audio2.ogg"
    audio1.write_bytes(b"fake")
    audio2.write_bytes(b"fake")

    mock_result = {"text": "Olá, teste de transcrição."}

    with patch("athena.whisper") as mock_whisper:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        out = transcribe_session([audio1, audio2], session_dir)

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "audio1.ogg" in content
    assert "audio2.ogg" in content
    assert "Olá, teste" in content
    assert not audio1.exists()
    assert not audio2.exists()
    assert (session_dir / "audios" / "audio1.ogg").exists()


def test_transcribe_header_contains_session_name(tmp_path):
    session_dir = tmp_path / "01-NEGOCIACAO_JOAO"
    (session_dir / "audios").mkdir(parents=True)
    audio = tmp_path / "test.ogg"
    audio.write_bytes(b"fake")

    with patch("athena.whisper") as mock_whisper:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "conteúdo"}
        mock_whisper.load_model.return_value = mock_model
        out = transcribe_session([audio], session_dir)

    content = out.read_text(encoding="utf-8")
    assert "01-NEGOCIACAO_JOAO" in content
```

- [ ] **Step 2: Rodar testes — confirmar FAIL**

Run: `python -m pytest tests/test_transcribe.py -v`

Expected: `ImportError` ou `AttributeError` — `transcribe_session` não existe ainda

- [ ] **Step 3: Adicionar transcribe_session ao athena.py**

Adicionar após `create_session_folder`:
```python
try:
    import whisper as whisper
except ImportError:
    whisper = None


def transcribe_session(audio_files: list, session_dir: Path) -> Path:
    if whisper is None:
        raise RuntimeError("openai-whisper não instalado. Run: pip install openai-whisper")
    model = whisper.load_model("medium")
    audios_dir = session_dir / "audios"
    parts = []
    for audio in sorted(audio_files):
        dest = audios_dir / audio.name
        shutil.move(str(audio), str(dest))
        result = model.transcribe(str(dest), language="pt")
        parts.append(f"### {audio.name}\n\n{result['text'].strip()}")
    dt = datetime.now()
    header = (
        f"# Transcrição — {session_dir.name}\n"
        f"**Data:** {dt.strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    )
    content = header + "\n\n---\n\n".join(parts)
    out = session_dir / "transcricao.md"
    out.write_text(content, encoding="utf-8")
    return out
```

- [ ] **Step 4: Rodar testes — confirmar PASS**

Run: `python -m pytest tests/test_session.py tests/test_transcribe.py -v`

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add athena.py tests/test_transcribe.py
git commit -m "feat(athena): stage 1 - whisper transcription pipeline"
```

---

## Task 4: Google Tasks push — Estágio 4

**Files:**
- Modify: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\athena.py` (adicionar push_tasks)
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\tests\test_push.py`

- [ ] **Step 1: Escrever testes de push**

`tests/test_push.py`:
```python
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from athena import push_tasks


def make_session(tmp_path):
    data = {
        "session_id": "2026-05-29_01-TEST",
        "tasks": [
            {
                "id": 1, "status": "pendente",
                "titulo": "🔴💰 JOÃO - Enviar proposta",
                "o_que_precisa": "Enviar proposta revisada",
                "mensagem_sugerida": "João, segue a proposta...",
                "observacoes": ["Incluir garantia"],
                "data": "2026-05-30",
            },
            {
                "id": 2, "status": "pendente",
                "titulo": "🟡🗒️ EU - Revisar contrato",
                "o_que_precisa": "Revisar cláusulas",
                "mensagem_sugerida": "",
                "observacoes": [],
                "data": "",
            },
        ],
    }
    (tmp_path / "tasks.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_push_only_approved_tasks(tmp_path):
    make_session(tmp_path)
    creds = tmp_path / "credentials.json"
    creds.write_text("{}", encoding="utf-8")
    token = tmp_path / "token.json"

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = "{}"
    mock_service = MagicMock()
    mock_service.tasks().insert().execute.return_value = {"id": "gtask_abc"}

    with patch("athena.Credentials") as MockCreds, \
         patch("athena.build", return_value=mock_service):
        MockCreds.from_authorized_user_file.return_value = mock_creds
        token.write_text("{}", encoding="utf-8")
        pushed = push_tasks(tmp_path, approved_ids=[1], creds_path=creds)

    assert len(pushed) == 1
    assert pushed[0]["id"] == 1
    assert pushed[0]["status"] == "enviada"

    data = json.loads((tmp_path / "tasks.json").read_text())
    statuses = {t["id"]: t["status"] for t in data["tasks"]}
    assert statuses[1] == "enviada"
    assert statuses[2] == "descartada"


def test_push_notes_includes_mensagem_and_observacoes(tmp_path):
    make_session(tmp_path)
    creds = tmp_path / "credentials.json"
    creds.write_text("{}", encoding="utf-8")
    (tmp_path / "token.json").write_text("{}", encoding="utf-8")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = "{}"
    captured_bodies = []
    mock_service = MagicMock()
    def capture_insert(tasklist, body):
        captured_bodies.append(body)
        m = MagicMock()
        m.execute.return_value = {"id": "x"}
        return m
    mock_service.tasks().insert = capture_insert

    with patch("athena.Credentials") as MockCreds, \
         patch("athena.build", return_value=mock_service):
        MockCreds.from_authorized_user_file.return_value = mock_creds
        push_tasks(tmp_path, approved_ids=[1], creds_path=creds)

    notes = captured_bodies[0]["notes"]
    assert "João, segue a proposta" in notes
    assert "Incluir garantia" in notes


def test_push_empty_approved_marks_all_discarded(tmp_path):
    make_session(tmp_path)
    creds = tmp_path / "credentials.json"
    creds.write_text("{}", encoding="utf-8")
    (tmp_path / "token.json").write_text("{}", encoding="utf-8")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = "{}"

    with patch("athena.Credentials") as MockCreds, \
         patch("athena.build") as mock_build:
        MockCreds.from_authorized_user_file.return_value = mock_creds
        pushed = push_tasks(tmp_path, approved_ids=[], creds_path=creds)

    assert pushed == []
    mock_build.assert_not_called()
```

- [ ] **Step 2: Rodar testes — confirmar FAIL**

Run: `python -m pytest tests/test_push.py -v`

Expected: `ImportError` — `push_tasks` não existe ainda

- [ ] **Step 3: Adicionar imports Google e push_tasks ao athena.py**

Adicionar após o bloco `try/except whisper`:
```python
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as build
except ImportError:
    Credentials = Request = InstalledAppFlow = build = None

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/tasks"]
```

Adicionar função após `transcribe_session`:
```python
def push_tasks(session_dir: Path, approved_ids: list, creds_path: Path) -> list:
    if Credentials is None:
        raise RuntimeError("google-api-python-client não instalado.")

    token_path = creds_path.parent / "token.json"
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    if not approved_ids:
        tasks_file = session_dir / "tasks.json"
        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        for task in data["tasks"]:
            task["status"] = "descartada"
        tasks_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return []

    service = build("tasks", "v1", credentials=creds)
    tasks_file = session_dir / "tasks.json"
    data = json.loads(tasks_file.read_text(encoding="utf-8"))
    pushed = []

    for task in data["tasks"]:
        if task["id"] not in approved_ids:
            task["status"] = "descartada"
            continue
        notes_parts = [task.get("o_que_precisa", "")]
        if task.get("mensagem_sugerida"):
            notes_parts.append(f"\n💬 Mensagem: {task['mensagem_sugerida']}")
        for obs in task.get("observacoes", []):
            notes_parts.append(f"📝 {obs}")
        body = {"title": task["titulo"], "notes": "\n".join(notes_parts)}
        if task.get("data"):
            body["due"] = f"{task['data']}T00:00:00.000Z"
        result = service.tasks().insert(tasklist="@default", body=body).execute()
        task["status"] = "enviada"
        task["google_task_id"] = result["id"]
        pushed.append(task)

    tasks_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return pushed
```

- [ ] **Step 4: Rodar todos os testes — confirmar PASS**

Run: `python -m pytest tests/ -v`

Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add athena.py tests/test_push.py
git commit -m "feat(athena): stage 4 - google tasks api integration"
```

---

## Task 5: CLI principal

**Files:**
- Modify: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\athena.py` (adicionar main + comandos)

- [ ] **Step 1: Adicionar CLI ao final de athena.py**

Substituir `if __name__ == "__main__": pass` por:

```python
def cmd_scan(args):
    base = Path(args.base_dir)
    files = find_loose_audios(base)
    if not files:
        print("NONE")
        sys.exit(0)
    for f in files:
        print(str(f))


def cmd_transcribe(args):
    base = Path(args.base_dir)
    files = find_loose_audios(base)
    if not files:
        print("ERROR: nenhum áudio encontrado em", base, file=sys.stderr)
        sys.exit(1)
    session_dir = create_session_folder(base, args.session_name)
    transcribe_session(files, session_dir)
    print(str(session_dir))


def cmd_push(args):
    session_dir = Path(args.session_dir)
    approved = [int(x) for x in args.approved.split(",") if x.strip()] if args.approved else []
    creds_path = Path(args.creds)
    pushed = push_tasks(session_dir, approved, creds_path)
    print(f"OK: {len(pushed)} task(s) enviada(s)")


def cmd_list(args):
    base = Path(args.base_dir)
    sessions = []
    for year_dir in sorted(base.iterdir()):
        if not year_dir.is_dir() or not re.match(r"^\d{4}$", year_dir.name):
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir():
                    continue
                for s in sorted(day_dir.iterdir()):
                    if s.is_dir() and re.match(r"^\d{2}-", s.name):
                        sessions.append(str(s))
    for s in sorted(sessions, reverse=True)[:10]:
        print(s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="athena")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Listar áudios soltos na raiz")
    p_scan.add_argument("--base-dir", required=True)

    p_tr = sub.add_parser("transcribe", help="Criar sessão e transcrever")
    p_tr.add_argument("--base-dir", required=True)
    p_tr.add_argument("--session-name", required=True)

    p_push = sub.add_parser("push", help="Enviar tasks para Google Tasks")
    p_push.add_argument("--session-dir", required=True)
    p_push.add_argument("--approved", default="")
    p_push.add_argument("--creds", required=True)

    p_list = sub.add_parser("list", help="Listar sessões recentes")
    p_list.add_argument("--base-dir", required=True)

    args = parser.parse_args()
    cmds = {"scan": cmd_scan, "transcribe": cmd_transcribe, "push": cmd_push, "list": cmd_list}
    cmds[args.cmd](args)
```

- [ ] **Step 2: Testar CLI manualmente**

Run: `python athena.py scan --base-dir "E:\OneDrive\01 - AUDIOLOGS"`

Expected: lista os 6 `.ogg` encontrados (ou `NONE` se já movidos)

- [ ] **Step 3: Rodar todos os testes — confirmar ainda PASS**

Run: `python -m pytest tests/ -v`

Expected: `12 passed`

- [ ] **Step 4: Commit**

```bash
git add athena.py
git commit -m "feat(athena): cli interface - scan/transcribe/push/list commands"
```

---

## Task 6: setup_google.py

**Files:**
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\setup_google.py`

- [ ] **Step 1: Criar setup_google.py**

```python
#!/usr/bin/env python3
"""Setup OAuth2 do Google para ATHENA (executa uma única vez)."""

from pathlib import Path


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ google-auth-oauthlib não instalado.")
        print("   Run: pip install google-auth-oauthlib")
        return

    tools_dir = Path(__file__).parent
    creds_path = tools_dir / "credentials.json"

    if not creds_path.exists():
        print(f"❌ credentials.json não encontrado em: {creds_path}")
        print()
        print("Como obter:")
        print("  1. Acesse https://console.cloud.google.com/")
        print("  2. Crie um projeto (ex: 'ATHENA')")
        print("  3. Ative a API: 'Google Tasks API'")
        print("  4. Crie credencial: OAuth 2.0 → Aplicativo de desktop")
        print("  5. Baixe o JSON e salve como: credentials.json nesta pasta")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path),
        ["https://www.googleapis.com/auth/tasks"]
    )
    creds = flow.run_local_server(port=0)

    token_path = tools_dir / "token.json"
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"✅ Autorização concluída. Token salvo em: {token_path}")
    print("   ATHENA está pronta para enviar tasks ao Google Tasks.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add setup_google.py
git commit -m "feat(athena): google oauth2 setup helper"
```

---

## Task 7: SKILL.md

**Files:**
- Create: `E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\SKILL.md`

- [ ] **Step 1: Criar SKILL.md**

```markdown
---
name: athena
description: Processa áudios de sessões de trabalho (WhatsApp, iPhone, reuniões) — transcreve, analisa, gera consultoria e envia tasks para Google Tasks. Invocar com /athena na pasta AUDIOLOGS.
---

# ATHENA — Consultora Pessoal de Negócios

Você é ATHENA. Quando invocada, processa sessões de áudio de Vinicius Abdalla (Tropico Solar).
Age como consultora de negócios: direta, honesta, tecnicamente precisa, sempre buscando o menor esforço para o usuário com resultado mais profissional.

## Configuração

- **Base dir:** `E:\OneDrive\01 - AUDIOLOGS`
- **Script:** `E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py`
- **Credenciais Google:** `E:\OneDrive\01 - AUDIOLOGS\_tools\credentials.json`

---

## Fluxo de Invocação

### Passo 1 — Detectar modo

```bash
python "E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py" scan --base-dir "E:\OneDrive\01 - AUDIOLOGS"
```

- Output `NONE` → **Modo Revisita** (ir para seção REVISITA)
- Output com arquivos → **Nova Sessão** (continuar Passo 2)

---

### Passo 2 — Confirmar nome da sessão

Diga ao usuário quantos áudios foram encontrados e proponha um nome inferido do contexto (ex: datas, nomes nos arquivos). Se o usuário disser "pode ser" ou não responder, use o nome proposto.

---

### Passo 3 — Criar pasta e transcrever

```bash
python "E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py" transcribe --base-dir "E:\OneDrive\01 - AUDIOLOGS" --session-name "[NOME_CONFIRMADO]"
```

O script imprime o caminho da sessão criada. Guarde esse caminho — é o `[SESSION_DIR]` usado nos próximos passos.

---

### Passo 4 — Analisar e escrever resumo.md

Leia `[SESSION_DIR]/transcricao.md`.

Escreva `[SESSION_DIR]/resumo.md` com esta estrutura **exata**:

```
# ATHENA — [YYYY-MM-DD] [NOME_SESSAO]

## Tipo de Sessão
[cliente / suporte-equatorial / suporte-inversor / distribuidora / brainstorm / outro]

## Participantes Detectados
- [pessoa ou entidade]

## Resumo Executivo
[2-3 parágrafos: o que aconteceu, o que está em jogo, estado atual]

## Situação Atual
[Estado objetivo — fatos, sem julgamento]

## Pontos de Atenção
- [risco, pendência ou oportunidade]

## Análise Técnica
[Dimensionamento, normas ABNT/ANEEL, especificações. Se não aplicável: N/A]

## Como Proceder
[Máximo 5 passos numerados — caminho mais simples e honesto]

## Comunicações Sugeridas
### Para [NOME]
> [Mensagem pronta — direta, profissional, pt-BR]
```

Seja específico. Sem frases de preenchimento. Use linguagem concreta.

---

### Passo 5 — Extrair tasks e apresentar para revisão

A partir da transcrição e do resumo, extraia todas as ações identificadas como cards ATHENA.

**Prioridades:**
| Código | Emoji | Nível |
|--------|-------|-------|
| 1 | 🔴 | Alta (Urgente — hoje/amanhã) |
| 2 | 🟠 | Média-Alta (essa semana) |
| 3 | 🟡 | Média-Baixa (próximas 2 semanas) |
| 4 | 🟢 | Baixa (sem pressa) |

**Categorias:**
| Código | Emoji | Categoria |
|--------|-------|-----------|
| 1 | 💰 | Vendas |
| 2 | 🗒️ | Escritório |
| 3 | 👷 | Obras |
| 4 | 😎 | Pessoal |
| 5 | 📋 | Pós-venda |

Escreva `[SESSION_DIR]/tasks.json`:
```json
{
  "session_id": "[YYYYMMDD]_[NN-NOME]",
  "tasks": [
    {
      "id": 1,
      "status": "pendente",
      "titulo": "[EMOJI_PRI][EMOJI_CAT] [RESPONSAVEL] - [descrição curta]",
      "prioridade": 1,
      "prioridade_emoji": "🔴",
      "prioridade_label": "Alta (Urgente)",
      "categoria": 1,
      "categoria_emoji": "💰",
      "categoria_label": "Vendas",
      "o_que_precisa": "[descrição detalhada da ação]",
      "responsavel": "[NOME ou EU]",
      "mensagem_sugerida": "[mensagem pronta ou string vazia]",
      "whatsapp": "[número internacional ou string vazia]",
      "observacoes": ["[obs1]", "[obs2]"],
      "data": "[YYYY-MM-DD ou string vazia]"
    }
  ]
}
```

Em seguida, apresente a lista de revisão:

```
📋 ATHENA — TASKS GERADAS
Sessão: [DATA] / [NOME]

  1. [🔴/🟠/🟡/🟢][💰/🗒️/👷/😎/📋] [RESPONSAVEL] - [titulo curto]   → [data ou "sem prazo"]
  2. ...

Quais enviar para o Google Tasks?
("todas", "nenhuma", ou números: "1 3 4")
```

---

### Passo 6 — Enviar tasks aprovadas

Parse da resposta:
- `"todas"` → todos os IDs
- `"nenhuma"` → lista vazia
- `"1 3 4"` → IDs [1, 3, 4]

```bash
python "E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py" push \
  --session-dir "[SESSION_DIR]" \
  --approved "[1,3,4]" \
  --creds "E:\OneDrive\01 - AUDIOLOGS\_tools\credentials.json"
```

Informe o resultado: `✅ [N] task(s) enviada(s) para o Google Tasks.`

---

## Modo Revisita

Quando `scan` retorna `NONE`:

1. Liste sessões recentes:
```bash
python "E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py" list --base-dir "E:\OneDrive\01 - AUDIOLOGS"
```

2. Pergunte qual sessão revisitar.

3. Leia `resumo.md` e `tasks.json` da sessão.

4. Mostre o estado atual e pergunte o que atualizar (prazos, observações, reativar tasks descartadas, enviar tasks pendentes).

5. Após mudanças, adicione entrada ao `CHANGELOG.md`:
```markdown
## [YYYY-MM-DD HH:MM] — Revisão
- [descrição da mudança]
```

6. Se houver tasks para enviar, execute o Passo 6.

---

## Tom e Estilo

- Português (pt-BR), direto, sem enrolação
- Honesto sobre riscos e problemas — não suavize demais
- Tecnicamente preciso em solar: normas ABNT NBR 16690, ANEEL RN 482/2012 e 687/2015, dimensionamento de string, inversor, proteções CA/CC
- Foco em menor esforço para Vinicius — sugira a ação mais simples que resolve o problema
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat(athena): main skill file - complete orchestration and analysis instructions"
```

---

## Task 8: Deploy

**Files:**
- Deploy: `SKILL.md` → `C:\Users\viniabdalla\.claude\skills\athena\SKILL.md`
- Deploy: `athena.py` → `E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py`
- Deploy: `setup_google.py` → `E:\OneDrive\01 - AUDIOLOGS\_tools\setup_google.py`

- [ ] **Step 1: Criar pasta do skill no Claude**

```powershell
New-Item -ItemType Directory -Force "C:\Users\viniabdalla\.claude\skills\athena"
```

- [ ] **Step 2: Copiar arquivos**

```powershell
Copy-Item "E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\SKILL.md" `
          "C:\Users\viniabdalla\.claude\skills\athena\SKILL.md" -Force

Copy-Item "E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\athena.py" `
          "E:\OneDrive\01 - AUDIOLOGS\_tools\athena.py" -Force

Copy-Item "E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\setup_google.py" `
          "E:\OneDrive\01 - AUDIOLOGS\_tools\setup_google.py" -Force
```

- [ ] **Step 3: Verificar skill registrado**

Run: `Get-Content "C:\Users\viniabdalla\.claude\skills\athena\SKILL.md" | Select-Object -First 5`

Expected: as primeiras 5 linhas do frontmatter do skill

- [ ] **Step 4: Testar invocação**

Numa nova sessão do Claude Code na pasta `E:\OneDrive\01 - AUDIOLOGS`, digitar `/athena` e confirmar que o skill é carregado e detecta os `.ogg` na raiz.

- [ ] **Step 5: Setup Google OAuth2 (uma vez)**

```powershell
# Coloque credentials.json em _tools/ antes desse passo
python "E:\OneDrive\01 - AUDIOLOGS\_tools\setup_google.py"
```

Expected: browser abre para autorizar, `token.json` salvo em `_tools/`

- [ ] **Step 6: Deploy para Codex (opcional)**

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills\athena"
Copy-Item "E:\OneDrive\CLAUDE CLI\00 - SKILLS\SKILL_ATHENA\SKILL.md" `
          "$env:USERPROFILE\.agents\skills\athena\SKILL.md" -Force
```

- [ ] **Step 7: Commit final**

```bash
git add .
git commit -m "feat(athena): deploy skill and tools to runtime locations"
```

---

## Checklist de Aceitação

- [ ] `/athena` detecta `.ogg`/`.m4a` soltos na raiz de AUDIOLOGS
- [ ] Cria pasta `2026/05-MAIO/29/01-NOME/` com sequencial correto
- [ ] `transcricao.md` gerado por Whisper em português
- [ ] `resumo.md` com todas as seções ATHENA preenchidas
- [ ] `tasks.json` com schema ATHENA correto (emojis, prioridade, categoria)
- [ ] Lista de revisão apresentada antes de enviar
- [ ] Tasks aprovadas aparecem no Google Tasks com título e notas corretos
- [ ] Tasks rejeitadas ficam com `"status": "descartada"` no JSON
- [ ] Modo revisita funciona sem áudios novos
- [ ] `CHANGELOG.md` registra todas as revisitas
