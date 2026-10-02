import yaml
from collections import Counter
from pathlib import Path
import re
from jinja2 import Environment, FileSystemLoader

# Directories
SCRIPT_DIR = Path(__file__).resolve().parent

#OUTPUT
CATALOG_PATH = SCRIPT_DIR / "Output" / "Leaderboard Tree.yaml"
PLAYERS_PATH = SCRIPT_DIR / "Output" / "Player Data.yaml"
FOLDER_WHITELIST_PATH = SCRIPT_DIR / "Input" / "Song Folder Whitelist.yaml"

#HTML
OUTPUT_HTML = SCRIPT_DIR / "docs" / "index.html"

DIFFICULTY_ORDER = ("Beginner", "Easy", "Medium", "Hard", "Challenge")
DIFFICULTY_RANK = {difficulty: rank for rank, difficulty in enumerate(DIFFICULTY_ORDER)}
PLAYER_PROFILE_SCORE_LIMIT = 20

def load_yaml_data():
    """Loads compiled databases directly from your output files."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    with open(PLAYERS_PATH, "r", encoding="utf-8") as f:
        players = yaml.safe_load(f)
    with open(FOLDER_WHITELIST_PATH, "r", encoding="utf-8") as f:
        folder_whitelist = yaml.safe_load(f)
    return catalog, players, folder_whitelist

def build_record_statistics(players, folder_whitelist):
    top_score_totals = Counter()
    first_place_scores = []
    hardest_difficulty_by_song = {}

    for player in players:
        player_name = player["player_name"]
        for score in player.get("scores", []):
            song_key = (score.get("section"), score.get("folder"), score.get("song"))
            difficulty = score.get("difficulty")
            if difficulty in DIFFICULTY_RANK:
                current_difficulty = hardest_difficulty_by_song.get(song_key)
                if current_difficulty is None or DIFFICULTY_RANK[difficulty] > DIFFICULTY_RANK[current_difficulty]:
                    hardest_difficulty_by_song[song_key] = difficulty

            if score.get("position") == 1:
                top_score_totals[player_name] += 1
                first_place_scores.append((player_name, score))

    eligible_players = {
        player_name
        for player_name, total in top_score_totals.items()
        if total >= 10
    }
    difficulty_counts = {difficulty: Counter() for difficulty in DIFFICULTY_ORDER}
    mix_counts = {section_name: Counter() for section_name in folder_whitelist}
    most_difficult_counts = Counter()

    for player_name, score in first_place_scores:
        if player_name not in eligible_players:
            continue

        difficulty = score.get("difficulty")
        if difficulty in difficulty_counts:
            difficulty_counts[difficulty][player_name] += 1

        song_key = (score.get("section"), score.get("folder"), score.get("song"))
        if difficulty == hardest_difficulty_by_song.get(song_key):
            most_difficult_counts[player_name] += 1

        section_name = score.get("section")
        if section_name in mix_counts:
            mix_counts[section_name][player_name] += 1

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

    mix_categories = []
    for section_name in folder_whitelist:
        category_key = re.sub(r"[^a-z0-9]+", "-", section_name.lower()).strip("-")
        mix_categories.extend(
            build_categories(
                [(category_key, section_name)],
                {category_key: mix_counts[section_name]},
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
        "mixes": mix_categories,
    }

def build_latest_plays(players, limit=100):
    entries = [
        {**score, "player": player["player_name"]}
        for player in players
        for score in player.get("scores", [])
    ]
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

def build_player_profiles(players, folder_whitelist):
    profiles = []
    player_profile_ids = {}

    for player_id, player in enumerate(players):
        player_name = player["player_name"]
        scores = player.get("scores", [])
        difficulty_counts = Counter(score.get("difficulty") for score in scores)
        mix_counts = Counter(score.get("section") for score in scores)
        ordered_difficulties = [
            difficulty for difficulty in DIFFICULTY_ORDER if difficulty_counts[difficulty]
        ]
        ordered_difficulties.extend(
            sorted(set(difficulty_counts) - set(DIFFICULTY_ORDER))
        )

        player_profile_ids[player_name] = player_id
        profiles.append({
            "player_name": player_name,
            "initials": player.get("initials", []),
            "difficulty_counts": [
                {"label": difficulty, "count": difficulty_counts[difficulty]}
                for difficulty in ordered_difficulties
            ],
            "mix_counts": [
                {"label": section, "count": mix_counts[section]}
                for section in folder_whitelist
            ],
            "scores": scores,
        })

    return profiles, player_profile_ids

def generate_html_with_jinja():
    catalog, players, folder_whitelist = load_yaml_data()
    record_statistics = build_record_statistics(players, folder_whitelist)
    latest_plays = build_latest_plays(players)
    player_profiles, player_profile_ids = build_player_profiles(players, folder_whitelist)
    
    # Configure Jinja environments to read your templates folder
    file_loader = FileSystemLoader(SCRIPT_DIR / "Input")
    env = Environment(loader=file_loader)
    
    # Load and compile the blueprint file
    template = env.get_template("template.html")
    
    # Pass data directly down to the Jinja template rendering scope
    rendered_output = template.render(
        catalog=catalog,
        players=players,
        record_statistics=record_statistics,
        latest_plays=latest_plays,
        player_profiles=player_profiles,
        player_profile_ids=player_profile_ids,
        player_profile_score_limit=PLAYER_PROFILE_SCORE_LIMIT,
    )
    
    # Export completed build to disk
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(rendered_output)
        
    print(f"Successfully generated clean Jinja2 leaderboard view to: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_html_with_jinja()
