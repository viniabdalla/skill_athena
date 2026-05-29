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
    (tmp_path / "arquivo.txt").write_text("")
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
