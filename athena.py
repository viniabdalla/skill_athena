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
    1: "01-JANEIRO", 2: "02-FEVEREIRO", 3: "03-MARÇO",   4: "04-ABRIL",
    5: "05-MAIO",    6: "06-JUNHO",     7: "07-JULHO",    8: "08-AGOSTO",
    9: "09-SETEMBRO",10: "10-OUTUBRO", 11: "11-NOVEMBRO", 12: "12-DEZEMBRO",
}

AUDIO_EXTS = {".ogg", ".m4a", ".mp3", ".wav"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp", ".gif", ".tiff"}

import os

try:
    import whisper as whisper
except ImportError:
    whisper = None

try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    Credentials = Request = InstalledAppFlow = build = None

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/tasks"]


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def find_loose_media(scan_dir: Path) -> dict:
    """Return {'audio': [...], 'image': [...]} of media files in scan_dir root."""
    audio, image = [], []
    for f in scan_dir.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in AUDIO_EXTS:
            audio.append(f)
        elif ext in IMAGE_EXTS:
            image.append(f)
    return {"audio": sorted(audio), "image": sorted(image)}


def find_loose_audios(base_dir: Path) -> list:
    return find_loose_media(base_dir)["audio"]


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


# ---------------------------------------------------------------------------
# Stage 1 — Transcription
# ---------------------------------------------------------------------------

def _transcribe_whisper(audio_files: list, session_dir: Path) -> list:
    if whisper is None:
        raise RuntimeError("openai-whisper não instalado. Run: pip install openai-whisper")
    model = whisper.load_model("medium")
    parts = []
    for audio in sorted(audio_files):
        result = model.transcribe(str(audio), language="pt")
        parts.append((audio.name, result["text"].strip()))
    return parts


def _transcribe_groq(audio_files: list, session_dir: Path) -> list:
    if GroqClient is None:
        raise RuntimeError("groq não instalado. Run: pip install groq")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        key_file = session_dir.parent.parent.parent.parent / "_tools" / "groq_key.txt"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. "
            "Defina a variável de ambiente ou salve a key em AUDIOLOGS/_tools/groq_key.txt"
        )
    client = GroqClient(api_key=api_key)
    parts = []
    for audio in sorted(audio_files):
        with open(audio, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(audio.name, f.read()),
                model="whisper-large-v3",
                language="pt",
                response_format="text",
            )
        parts.append((audio.name, result.strip() if isinstance(result, str) else result.text.strip()))
    return parts


def move_images(image_files: list, session_dir: Path) -> list:
    """Move image files into session_dir/media/ and return new paths."""
    media_dir = session_dir / "media"
    media_dir.mkdir(exist_ok=True)
    moved = []
    for img in image_files:
        dest = media_dir / img.name
        shutil.move(str(img), str(dest))
        moved.append(dest)
    return moved


def transcribe_session(audio_files: list, session_dir: Path, engine: str = "whisper") -> Path:
    audios_dir = session_dir / "audios"
    for audio in audio_files:
        shutil.move(str(audio), str(audios_dir / audio.name))
    moved = [audios_dir / a.name for a in audio_files]

    if engine == "groq":
        parts_data = _transcribe_groq(moved, session_dir)
    else:
        parts_data = _transcribe_whisper(moved, session_dir)

    parts = [f"### {name}\n\n{text}" for name, text in parts_data]
    dt = datetime.now()
    header = (
        f"# Transcrição — {session_dir.name}\n"
        f"**Data:** {dt.strftime('%Y-%m-%d %H:%M')}  |  **Engine:** {engine}\n\n---\n\n"
    )
    content = header + "\n\n---\n\n".join(parts)
    out = session_dir / "transcricao.md"
    out.write_text(content, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Stage 4 — Google Tasks push
# ---------------------------------------------------------------------------

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

    tasks_file = session_dir / "tasks.json"
    data = json.loads(tasks_file.read_text(encoding="utf-8"))

    if not approved_ids:
        for task in data["tasks"]:
            task["status"] = "descartada"
        tasks_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return []

    service = build("tasks", "v1", credentials=creds)
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_scan(args):
    scan_dir = Path(args.scan_dir) if args.scan_dir else Path.cwd()
    media = find_loose_media(scan_dir)
    if not media["audio"] and not media["image"]:
        print("NONE")
        return
    for f in media["audio"]:
        print(f"AUDIO\t{f}")
    for f in media["image"]:
        print(f"IMAGE\t{f}")


def cmd_transcribe(args):
    scan_dir = Path(args.scan_dir) if args.scan_dir else Path.cwd()
    base_dir = Path(args.base_dir)
    media = find_loose_media(scan_dir)
    if not media["audio"] and not media["image"]:
        print("ERROR: nenhum arquivo encontrado em", scan_dir, file=sys.stderr)
        sys.exit(1)
    session_dir = create_session_folder(base_dir, args.session_name)
    if media["audio"]:
        transcribe_session(media["audio"], session_dir, engine=args.engine)
    if media["image"]:
        moved = move_images(media["image"], session_dir)
        print(f"IMAGES\t{len(moved)}\t{session_dir / 'media'}")
    print(str(session_dir))


def cmd_push(args):
    session_dir = Path(args.session_dir)
    approved = [int(x) for x in args.approved.split(",") if x.strip()] if args.approved else []
    pushed = push_tasks(session_dir, approved, Path(args.creds))
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

    p = sub.add_parser("scan")
    p.add_argument("--scan-dir", default=None, help="Pasta a varrer (padrão: pasta atual)")

    p = sub.add_parser("transcribe")
    p.add_argument("--scan-dir", default=None, help="Pasta de origem dos arquivos (padrão: pasta atual)")
    p.add_argument("--base-dir", required=True, help="Base AUDIOLOGS onde a sessão será criada")
    p.add_argument("--session-name", required=True)
    p.add_argument("--engine", choices=["whisper", "groq"], default="groq")

    p = sub.add_parser("push")
    p.add_argument("--session-dir", required=True)
    p.add_argument("--approved", default="")
    p.add_argument("--creds", required=True)

    p = sub.add_parser("list")
    p.add_argument("--base-dir", required=True)

    args = parser.parse_args()
    {"scan": cmd_scan, "transcribe": cmd_transcribe, "push": cmd_push, "list": cmd_list}[args.cmd](args)
