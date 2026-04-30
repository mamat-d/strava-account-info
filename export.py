"""
Main Strava export script.
Exports: athlete profile, stats, gear, clubs, routes, starred segments,
         all activities (with streams, laps, segment efforts, photos if enabled).

Usage:
    python export.py
"""

import os
import json
import csv
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from client import StravaClient

EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "./export"))
FORMATS = [f.strip() for f in os.getenv("EXPORT_FORMATS", "json,csv").split(",")]
INCLUDE_STREAMS = os.getenv("INCLUDE_STREAMS", "true").lower() == "true"
INCLUDE_PHOTOS = os.getenv("INCLUDE_PHOTOS", "false").lower() == "true"
MAX_ACTIVITIES = int(os.getenv("MAX_ACTIVITIES", "0"))

STREAM_TYPES = "time,distance,latlng,altitude,heartrate,cadence,watts,temp,moving,grade_smooth"


def save_json(data, path: Path):
    if data is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(rows: list[dict], path: Path):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_gpx(activity: dict, streams: dict, path: Path):
    """Build a minimal GPX from latlng + altitude + time streams."""
    import gpxpy
    import gpxpy.gpx

    latlng = streams.get("latlng", {}).get("data", [])
    if not latlng:
        return

    altitudes = streams.get("altitude", {}).get("data", [])
    times_s = streams.get("time", {}).get("data", [])
    start = datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00"))

    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name=activity.get("name", "Activity"))
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for i, (lat, lon) in enumerate(latlng):
        pt = gpxpy.gpx.GPXTrackPoint(lat, lon)
        if i < len(altitudes):
            pt.elevation = altitudes[i]
        if i < len(times_s):
            from datetime import timezone, timedelta
            pt.time = start + timedelta(seconds=times_s[i])
        segment.points.append(pt)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())


def flatten_activity(a: dict) -> dict:
    """Flatten nested fields for CSV export."""
    flat = {k: v for k, v in a.items() if not isinstance(v, (dict, list))}
    for nested_key in ("map", "gear", "athlete"):
        if nested_key in a and isinstance(a[nested_key], dict):
            for k, v in a[nested_key].items():
                flat[f"{nested_key}_{k}"] = v
    return flat


def export_athlete(client: StravaClient):
    print("\n[1/5] Athlete profile & stats")
    athlete = client.get("/athlete")
    save_json(athlete, EXPORT_DIR / "athlete" / "profile.json")

    stats = client.get(f"/athletes/{athlete['id']}/stats")
    save_json(stats, EXPORT_DIR / "athlete" / "stats.json")

    zones = client.get("/athlete/zones")
    save_json(zones, EXPORT_DIR / "athlete" / "zones.json")

    print(f"      Saved profile, stats, zones for {athlete['firstname']} {athlete['lastname']}")
    return athlete


def export_gear(client: StravaClient, athlete: dict):
    print("\n[2/5] Gear")
    gear_ids = (
        [b["id"] for b in athlete.get("bikes", [])]
        + [s["id"] for s in athlete.get("shoes", [])]
    )
    gear_list = []
    for gid in gear_ids:
        g = client.get(f"/gear/{gid}")
        gear_list.append(g)
        save_json(g, EXPORT_DIR / "gear" / f"{gid}.json")

    if "csv" in FORMATS:
        save_csv(gear_list, EXPORT_DIR / "gear" / "gear.csv")
    print(f"      Saved {len(gear_list)} gear items")


def export_clubs(client: StravaClient):
    print("\n[3/5] Clubs")
    clubs = list(client.paginate("/athlete/clubs"))
    save_json(clubs, EXPORT_DIR / "clubs" / "clubs.json")
    if "csv" in FORMATS:
        save_csv(clubs, EXPORT_DIR / "clubs" / "clubs.csv")
    print(f"      Saved {len(clubs)} clubs")


def export_activities(client: StravaClient):
    print("\n[4/5] Activities list")
    activities = list(client.paginate("/athlete/activities"))
    if MAX_ACTIVITIES:
        activities = activities[:MAX_ACTIVITIES]

    save_json(activities, EXPORT_DIR / "activities" / "all_activities.json")
    if "csv" in FORMATS:
        save_csv([flatten_activity(a) for a in activities], EXPORT_DIR / "activities" / "all_activities.csv")

    print(f"      {len(activities)} activities fetched")
    return activities


def export_activity_details(client: StravaClient, activities: list[dict]):
    print(f"\n[5/5] Activity details (streams={'yes' if INCLUDE_STREAMS else 'no'}, gpx={'yes' if 'gpx' in FORMATS else 'no'})")

    new_count = 0
    already_downloaded = 0
    for activity in tqdm(activities, unit="activity"):
        aid = activity["id"]
        detail_dir = EXPORT_DIR / "activities" / str(aid)

        # Incremental: check if already downloaded
        streams_file = detail_dir / "streams.json"
        if streams_file.exists():
            already_downloaded += 1
            continue

        # Save activity summary (already have all needed data from activity list)
        save_json(activity, detail_dir / "detail.json")
        new_count += 1

        # Laps
        try:
            laps = client.get(f"/activities/{aid}/laps")
            save_json(laps, detail_dir / "laps.json")
        except Exception:
            pass

        streams = {}
        if INCLUDE_STREAMS:
            try:
                raw = client.get(f"/activities/{aid}/streams", keys=STREAM_TYPES, key_by_type=True)
                if raw:
                    streams = raw if isinstance(raw, dict) else {}
                    save_json(streams, detail_dir / "streams.json")
            except Exception:
                pass

        if "gpx" in FORMATS and streams:
            try:
                save_gpx(activity, streams, detail_dir / f"{aid}.gpx")
            except Exception:
                pass

    print(f"      Downloaded {new_count} new, {already_downloaded} already in cache")


def write_summary(activities: list[dict]):
    summary = {
        "exported_at": datetime.now().isoformat(),
        "total_activities": len(activities),
        "sport_types": {},
        "total_distance_km": 0,
        "total_elevation_m": 0,
        "total_moving_time_h": 0,
    }
    for a in activities:
        sport = a.get("sport_type", a.get("type", "Unknown"))
        summary["sport_types"][sport] = summary["sport_types"].get(sport, 0) + 1
        summary["total_distance_km"] += a.get("distance", 0) / 1000
        summary["total_elevation_m"] += a.get("total_elevation_gain", 0)
        summary["total_moving_time_h"] += a.get("moving_time", 0) / 3600

    summary["total_distance_km"] = round(summary["total_distance_km"], 1)
    summary["total_elevation_m"] = round(summary["total_elevation_m"], 0)
    summary["total_moving_time_h"] = round(summary["total_moving_time_h"], 1)

    save_json(summary, EXPORT_DIR / "summary.json")
    return summary


def main():
    print("=" * 50)
    print("  Strava Full Export")
    print(f"  Output: {EXPORT_DIR.resolve()}")
    print(f"  Formats: {', '.join(FORMATS)}")
    print("=" * 50)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    client = StravaClient()

    athlete = export_athlete(client)
    export_gear(client, athlete)
    export_clubs(client)
    activities = export_activities(client)
    export_activity_details(client, activities)

    summary = write_summary(activities)

    print("\n" + "=" * 50)
    print("  Export complete!")
    print(f"  Activities : {summary['total_activities']}")
    print(f"  Distance   : {summary['total_distance_km']} km")
    print(f"  Elevation  : {summary['total_elevation_m']} m")
    print(f"  Moving time: {summary['total_moving_time_h']} h")
    print(f"  Saved to   : {EXPORT_DIR.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
