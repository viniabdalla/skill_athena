from unittest.mock import patch, MagicMock
from pathlib import Path
from athena import transcribe_session


def test_transcribe_whisper_moves_files_and_creates_output(tmp_path):
    session_dir = tmp_path / "01-TEST"
    (session_dir / "audios").mkdir(parents=True)

    audio1 = tmp_path / "audio1.ogg"
    audio2 = tmp_path / "audio2.ogg"
    audio1.write_bytes(b"fake")
    audio2.write_bytes(b"fake")

    with patch("athena.whisper") as mock_whisper:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Olá, teste de transcrição."}
        mock_whisper.load_model.return_value = mock_model

        out = transcribe_session([audio1, audio2], session_dir, engine="whisper")

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "audio1.ogg" in content
    assert "audio2.ogg" in content
    assert "Olá, teste" in content
    assert not audio1.exists()
    assert not audio2.exists()
    assert (session_dir / "audios" / "audio1.ogg").exists()


def test_transcribe_header_contains_engine(tmp_path):
    session_dir = tmp_path / "01-NEGOCIACAO_JOAO"
    (session_dir / "audios").mkdir(parents=True)
    audio = tmp_path / "test.ogg"
    audio.write_bytes(b"fake")

    with patch("athena.whisper") as mock_whisper:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "conteúdo"}
        mock_whisper.load_model.return_value = mock_model
        out = transcribe_session([audio], session_dir, engine="whisper")

    content = out.read_text(encoding="utf-8")
    assert "01-NEGOCIACAO_JOAO" in content
    assert "whisper" in content


def test_transcribe_groq_calls_api_and_creates_output(tmp_path):
    session_dir = tmp_path / "01-TEST"
    (session_dir / "audios").mkdir(parents=True)

    audio = tmp_path / "audio1.ogg"
    audio.write_bytes(b"fake")

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = "Texto transcrito pelo Groq."

    with patch("athena.GroqClient", return_value=mock_client), \
         patch("athena.os.environ.get", return_value="fake-groq-key"):
        out = transcribe_session([audio], session_dir, engine="groq")

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "audio1.ogg" in content
    assert "Texto transcrito pelo Groq" in content
    assert "groq" in content
    mock_client.audio.transcriptions.create.assert_called_once()
