# strava-export

Export complet de toutes tes données Strava en local — activités, GPS, fréquence cardiaque, puissance, gear, clubs, routes et segments. Formats JSON, CSV et GPX.

## Prérequis

- Python 3.10+
- Une app Strava : [strava.com/settings/api](https://www.strava.com/settings/api)

## Installation

```bash
git clone https://github.com/your-username/strava-export
cd strava-export
```

**Installer les dépendances via `pyproject.toml`** (recommandé)
```bash
pip install -e .
```

Les dépendances sont définies dans `pyproject.toml` et maintenues à jour. Le fichier `requirements.txt` est généré automatiquement depuis `pyproject.toml` avec les versions exactes pour reproductibilité.

**Configure les credentials**
```bash
cp .env.example .env
```

Ouvre `.env` et renseigne `STRAVA_CLIENT_ID` et `STRAVA_CLIENT_SECRET` depuis [strava.com/settings/api](https://www.strava.com/settings/api).

## Utilisation

**1. Authentification** (une seule fois)

```bash
python auth.py
```

Ouvre le navigateur sur la page d'autorisation Strava. Après validation, les tokens sont écrits automatiquement dans `.env`.

**2. Export**

```bash
python export.py
```

L'export est incrémental : les activités déjà téléchargées sont ignorées. Tu peux relancer sans risque.

## Ce qui est exporté

| Donnée | Fichier |
|---|---|
| Profil athlète | `athlete/profile.json` |
| Statistiques globales | `athlete/stats.json` |
| Zones cardiaques | `athlete/zones.json` |
| Équipements | `gear/gear.csv` + `gear/{id}.json` |
| Clubs | `clubs/clubs.json` |
| Routes | `routes/routes.json` |
| Segments favoris | `segments/starred.json` |
| Toutes les activités | `activities/all_activities.{json,csv}` |
| Détail par activité | `activities/{id}/detail.json` |
| Tours / splits | `activities/{id}/laps.json` |
| Streams GPS, FC, puissance | `activities/{id}/streams.json` |
| Fichier GPX | `activities/{id}/{id}.gpx` |
| Récap global | `summary.json` |

## Structure complète

```
export/
├── summary.json
├── athlete/
│   ├── profile.json
│   ├── stats.json
│   └── zones.json
├── gear/
│   ├── gear.csv
│   └── {id}.json
├── clubs/
│   └── clubs.json
├── routes/
│   └── routes.json
├── segments/
│   └── starred.json
└── activities/
    ├── all_activities.json
    ├── all_activities.csv
    └── {id}/
        ├── detail.json
        ├── laps.json
        ├── streams.json
        └── {id}.gpx
```

## Configuration

Toutes les options sont dans `.env` (voir `.env.example`) :

| Variable | Description | Défaut |
|---|---|---|
| `STRAVA_CLIENT_ID` | Client ID de ton app Strava | — |
| `STRAVA_CLIENT_SECRET` | Client Secret | — |
| `STRAVA_ACCESS_TOKEN` | Généré automatiquement par `auth.py` | — |
| `STRAVA_REFRESH_TOKEN` | Généré automatiquement par `auth.py` | — |
| `EXPORT_DIR` | Dossier de destination | `./export` |
| `EXPORT_FORMATS` | Formats : `json`, `csv`, `gpx` | `json,csv` |
| `INCLUDE_STREAMS` | Streams GPS / FC / puissance | `true` |
| `INCLUDE_PHOTOS` | Photos des activités | `false` |
| `MAX_ACTIVITIES` | Limite (0 = toutes) | `0` |

## Rate limiting

L'API Strava est limitée à 100 requêtes / 15 min et 1000 / jour. Le client gère le backoff automatiquement. Pour un gros compte (500+ activités avec streams), compte environ 30–60 min au premier lancement.

## Analyser les données avec Claude

Une fois l'export terminé, donne à Claude :

```
export/summary.json
export/activities/all_activities.json
```

Exemples de questions : progression sur 12 mois, répartition par sport, évolution FC, kilométrage par équipement, détection de surmenage, génération de graphiques.

## Licence

MIT
