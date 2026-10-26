import yaml
from collections import Counter
from pathlib import Path
import re
from jinja2 import Environment, FileSystemLoader

# Directories
SCRIPT_DIR = Path(__file__).resolve().parent

#OUTPUT
SONG_CATALOG_PATH = SCRIPT_DIR / "Output" / "Song Leaderboard Tree.yaml"
COURSE_CATALOG_PATH = SCRIPT_DIR / "Output" / "Course Leaderboard Tree.yaml"
PLAYERS_PATH = SCRIPT_DIR / "Output" / "Player Data.yaml"
FOLDER_WHITELIST_PATH = SCRIPT_DIR / "Input" / "Song Folder Whitelist.yaml"
COURSE_PACK_WHITELIST_PATH = SCRIPT_DIR / "Input" / "Course Pack Whitelist.yaml"

#HTML
OUTPUT_HTML = SCRIPT_DIR / "docs" / "index.html"
SOURCE_CSS = SCRIPT_DIR / "Input" / "leaderboard.css"
OUTPUT_CSS = OUTPUT_HTML.parent / "leaderboard.css"

DIFFICULTY_ORDER = ("Beginner", "Easy", "Medium", "Hard", "Challenge")
DIFFICULTY_RANK = {difficulty: rank for rank, difficulty in enumerate(DIFFICULTY_ORDER)}
PLAYER_PROFILE_SCORE_LIMIT = 20

def load_yaml_data():
    """Loads compiled databases directly from your output files."""
    with open(SONG_CATALOG_PATH, "r", encoding="utf-8") as f:
        song_catalog = yaml.safe_load(f)
    with open(COURSE_CATALOG_PATH, "r", encoding="utf-8") as f:
        course_catalog = yaml.safe_load(f)
    with open(PLAYERS_PATH, "r", encoding="utf-8") as f:
        players = yaml.safe_load(f)
    with open(FOLDER_WHITELIST_PATH, "r", encoding="utf-8") as f:
        folder_whitelist = yaml.safe_load(f)
    with open(COURSE_PACK_WHITELIST_PATH, "r", encoding="utf-8") as f:
        course_pack_whitelist = yaml.safe_load(f)
    return song_catalog, course_catalog, players, folder_whitelist, course_pack_whitelist

def build_entity_record_statistics(players, score_key, grouping_key, grouping_names, identity_keys):
    top_score_totals = Counter()
    first_place_scores = []
    hardest_difficulty_by_entity = {}

    for player in players:
        player_name = player["player_name"]
        for score in player.get(score_key, []):
            entity_key = tuple(score.get(key) for key in identity_keys)
            difficulty = score.get("difficulty")
            if difficulty in DIFFICULTY_RANK:
                current_difficulty = hardest_difficulty_by_entity.get(entity_key)
                if current_difficulty is None or DIFFICULTY_RANK[difficulty] > DIFFICULTY_RANK[current_difficulty]:
                    hardest_difficulty_by_entity[entity_key] = difficulty

            if score.get("position") == 1:
                top_score_totals[player_name] += 1
                first_place_scores.append((player_name, score))

    eligible_players = {
        player_name
        for player_name, total in top_score_totals.items()
        if total >= 10
    }
    difficulty_counts = {difficulty: Counter() for difficulty in DIFFICULTY_ORDER}
    grouping_counts = {name: Counter() for name in grouping_names}
    most_difficult_counts = Counter()

    for player_name, score in first_place_scores:
        if player_name not in eligible_players:
            continue

        difficulty = score.get("difficulty")
        if difficulty in difficulty_counts:
            difficulty_counts[difficulty][player_name] += 1

        entity_key = tuple(score.get(key) for key in identity_keys)
        if difficulty == hardest_difficulty_by_entity.get(entity_key):
            most_difficult_counts[player_name] += 1

        grouping_name = score.get(grouping_key)
        if grouping_name in grouping_counts:
            grouping_counts[grouping_name][player_name] += 1

    def build_categories(category_definitions, counts):
        categories = []
        for key, label in category_definitions:
            leaders = [
                {"player": player_name, "wins": wins}
                for player_name, wins in sorted(
                    counts[key].items(), key=lambda item: (-item[1], item[0])
                )
            ]
            categories.append({"key": key, "label": label, "leaders": leaders})
        return categories

    grouping_categories = []
    for grouping_name in grouping_names:
        category_key = re.sub(r"[^a-z0-9]+", "-", grouping_name.lower()).strip("-")
        grouping_categories.extend(
            build_categories(
                [(category_key, grouping_name)],
                {category_key: grouping_counts[grouping_name]},
            )
        )

    difficulty_categories = build_categories(
        [(difficulty.lower(), difficulty) for difficulty in DIFFICULTY_ORDER],
        {difficulty.lower(): difficulty_counts[difficulty] for difficulty in DIFFICULTY_ORDER},
    )
    difficulty_categories.append({
        "key": "most-difficult",
        "label": "Most Difficult",
        "leaders": [
            {"player": player_name, "wins": wins}
            for player_name, wins in sorted(
                most_difficult_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    })

    return {
        "qualified_players": len(eligible_players),
        "minimum_top_scores": 10,
        "difficulties": difficulty_categories,
        "groupings": grouping_categories,
    }

def build_record_statistics(players, folder_whitelist, course_pack_whitelist):
    return {
        "songs": build_entity_record_statistics(
            players,
            "song_scores",
            "section",
            list(folder_whitelist),
            ("section", "folder", "song"),
        ),
        "courses": build_entity_record_statistics(
            players,
            "course_scores",
            "classification",
            list(course_pack_whitelist),
            ("classification", "pack", "course"),
        ),
    }

def build_latest_pbs(players, limit=100):
    entries = []
    for player in players:
        entries.extend(
            {**score, "player": player["player_name"], "record_type": "Song"}
            for score in player.get("song_scores", [])
        )
        entries.extend(
            {**score, "player": player["player_name"], "record_type": "Course"}
            for score in player.get("course_scores", [])
        )
    entries.sort(key=date_sort_key, reverse=True)
    machine_records = [entry for entry in entries if entry.get("position") == 1]
    return {
        "all": entries[:limit],
        "machine_records": machine_records[:limit],
    }

def date_sort_key(entry):
    played = entry.get("date")
    if not isinstance(played, str) or played == "Unknown Date":
        return (False, "")
    return (True, played)

def build_player_standings(players):
    standings = []
    for player in players:
        song_scores = player.get("song_scores", [])
        course_scores = player.get("course_scores", [])
        song_records = sum(score.get("position") == 1 for score in song_scores)
        course_records = sum(score.get("position") == 1 for score in course_scores)
        standings.append({
            **player,
            "song_top_records": song_records,
            "course_top_records": course_records,
            "total_scores": len(song_scores) + len(course_scores),
        })

    standings.sort(
        key=lambda player: (
            -(player["song_top_records"] + player["course_top_records"]),
            player["player_name"],
        )
    )
    return standings

def build_player_profiles(players, folder_whitelist, course_pack_whitelist):
    profiles = []
    player_profile_ids = {}

    for player_id, player in enumerate(players):
        player_name = player["player_name"]
        song_scores = [
            {**score, "record_type": "song"}
            for score in player.get("song_scores", [])
        ]
        course_scores = [
            {**score, "record_type": "course"}
            for score in player.get("course_scores", [])
        ]

        def build_difficulty_counts(scores):
            counts = Counter(score.get("difficulty") for score in scores)
            ordered = [difficulty for difficulty in DIFFICULTY_ORDER if counts[difficulty]]
            ordered.extend(sorted(set(counts) - set(DIFFICULTY_ORDER)))
            return [{"label": difficulty, "count": counts[difficulty]} for difficulty in ordered]

        song_mix_counts = Counter(score.get("section") for score in song_scores)
        course_classification_counts = Counter(score.get("classification") for score in course_scores)

        player_profile_ids[player_name] = player_id
        profiles.append({
            "player_name": player_name,
            "initials": player.get("initials", []),
            "song_difficulty_counts": build_difficulty_counts(song_scores),
            "song_group_counts": [
                {"label": section, "count": song_mix_counts[section]}
                for section in folder_whitelist
            ],
            "course_difficulty_counts": build_difficulty_counts(course_scores),
            "course_group_counts": [
                {"label": classification, "count": course_classification_counts[classification]}
                for classification in course_pack_whitelist
            ],
            "song_scores": song_scores,
            "course_scores": course_scores,
        })

    return profiles, player_profile_ids

def generate_html_with_jinja():
    song_catalog, course_catalog, players, folder_whitelist, course_pack_whitelist = load_yaml_data()
    record_statistics = build_record_statistics(players, folder_whitelist, course_pack_whitelist)
    latest_pbs = build_latest_pbs(players)
    player_standings = build_player_standings(players)
    player_profiles, player_profile_ids = build_player_profiles(
        players,
        folder_whitelist,
        course_pack_whitelist,
    )
    
    # Configure Jinja environments to read your templates folder
    file_loader = FileSystemLoader(SCRIPT_DIR / "Input")
    env = Environment(loader=file_loader)
    
    # Load and compile the blueprint file
    template = env.get_template("template.html")
    
    # Pass data directly down to the Jinja template rendering scope
    rendered_output = template.render(
        song_catalog=song_catalog,
        course_catalog=course_catalog,
        players=player_standings,
        record_statistics=record_statistics,
        latest_pbs=latest_pbs,
        player_profiles=player_profiles,
        player_profile_ids=player_profile_ids,
        player_profile_score_limit=PLAYER_PROFILE_SCORE_LIMIT,
    )
    
    # Export completed build to disk
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSS.write_text(SOURCE_CSS.read_text(encoding="utf-8"), encoding="utf-8")
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(rendered_output)
        
    print(f"Successfully generated clean Jinja2 leaderboard view to: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_html_with_jinja()
