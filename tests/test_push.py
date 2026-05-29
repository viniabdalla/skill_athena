import json
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
    (tmp_path / "token.json").write_text("{}", encoding="utf-8")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = "{}"
    mock_service = MagicMock()
    mock_service.tasks().insert().execute.return_value = {"id": "gtask_abc"}

    with patch("athena.Credentials") as MockCreds, \
         patch("athena.build", return_value=mock_service):
        MockCreds.from_authorized_user_file.return_value = mock_creds
        pushed = push_tasks(tmp_path, approved_ids=[1], creds_path=creds)

    assert len(pushed) == 1
    assert pushed[0]["id"] == 1
    assert pushed[0]["status"] == "enviada"

    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
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
    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert all(t["status"] == "descartada" for t in data["tasks"])
