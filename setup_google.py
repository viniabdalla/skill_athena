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
        print(f"ERRO: credentials.json nao encontrado em: {creds_path}")
        print()
        print("Como obter:")
        print("  1. Acesse https://console.cloud.google.com/")
        print("  2. Crie um projeto (ex: ATHENA)")
        print("  3. Ative a API: Google Tasks API")
        print("  4. Crie credencial: OAuth 2.0 -> Aplicativo de desktop")
        print("  5. Baixe o JSON e salve como: credentials.json nesta pasta")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path),
        ["https://www.googleapis.com/auth/tasks"]
    )
    creds = flow.run_local_server(port=0)

    token_path = tools_dir / "token.json"
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"OK! Token salvo em: {token_path}")
    print("ATHENA esta pronta para enviar tasks ao Google Tasks.")


if __name__ == "__main__":
    main()
