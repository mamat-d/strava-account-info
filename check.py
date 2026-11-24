"""Diagnostic: vérifie que le token est valide et a les bons scopes."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("STRAVA_ACCESS_TOKEN", "")
print(f"Token chargé : {'oui' if token else 'NON — manquant dans .env'}")
if token:
    print(f"Token (début) : {token[:8]}...")

resp = requests.get(
    "https://www.strava.com/api/v3/athlete",
    headers={"Authorization": f"Bearer {token}"},
)

print(f"\nStatut HTTP : {resp.status_code}")
print(f"Réponse     : {resp.json()}")
