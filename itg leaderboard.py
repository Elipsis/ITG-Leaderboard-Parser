import xml.etree.ElementTree as ET
import re
import yaml
import html_generator
from operator import attrgetter
from datetime import datetime
from pathlib import Path

#Directory
SCRIPT_DIR = Path(__file__).resolve().parent

#INPUTS
SONG_FOLDER_WHITELIST = SCRIPT_DIR / "Input" / "Song Folder Whitelist.yaml"
COURSE_PACK_WHITELIST = SCRIPT_DIR / "Input" / "Course Pack Whitelist.yaml"
ITG2_WHITELIST = SCRIPT_DIR / "Input" / "ITG2 Whitelist.txt"
PLAYER_ALIASES = SCRIPT_DIR / "Input" / "Profile Initials.yaml"

#OUTPUTS
SONG_CATALOG = SCRIPT_DIR / "Output" / "Song Leaderboard Tree.yaml"
COURSE_CATALOG = SCRIPT_DIR / "Output" / "Course Leaderboard Tree.yaml"
PLAYERS = SCRIPT_DIR / "Output" / "Player Data.yaml"
ITG2_BLACKLIST = SCRIPT_DIR / "Output" / "ITG2 Purges.txt"

DIFFICULTY_ORDER = ("Beginner", "Easy", "Medium", "Hard", "Challenge", "Edit")

class XML_Song_Record:
    def __init__(self, inits, folder, song, difficulty, type, percentage, grade, award, date):
        self.inits = inits
        self.folder = folder
        self.song = song
        self.difficulty = difficulty
        self.type = type
        self.percentage = percentage
        self.grade = grade
        self.award = award
        self.date = date

    def __str__(self):
        return f"{self.song} - ({self.difficulty}): {self.percentage} by {self.inits}"

class XML_Course_Record:
    def __init__(self, inits, pack, course, difficulty, type, percentage, grade, award, date):
        self.inits = inits
        self.pack = pack
        self.course = course
        self.difficulty = difficulty
        self.type = type
        self.percentage = percentage
        self.grade = grade
        self.award = award
        self.date = date

    def __str__(self):
        return f"{self.course} - ({self.difficulty}): {self.percentage} by {self.inits}"

### Song Classes ###
class Section:
    def __init__(self, name):
        self.name = name
        self.folders = []

    def add_folder(self, folder):
        self.folders.append(folder)

    @property
    def num_folders(self):
        return len(self.folders)

    def __str__(self):
        return f"{self.name} containing {self.num_folders} folders"
    
class Folder:
    def __init__(self, name):
        self.name = name
        self.songs = []

    def add_song(self, song):
        self.songs.append(song)

    @property
    def num_songs(self):
        return len(self.songs)

    def __str__(self):
        return f"{self.name} containing {self.num_songs} songs"

class Song:
    def __init__(self, name):
        self.name = name
        self.difficulties_single = []
        self.difficulties_double = []
        self.leaderboards = {}

    def add_difficulty(self, difficulty, type):
        match type:
            case "single":
                if difficulty not in self.difficulties_single:
                    self.difficulties_single.append(difficulty)
            case "double":
                if difficulty not in self.difficulties_double:
                    self.difficulties_double.append(difficulty)
            case _:
                print(f"Unknown type '{type}' for song '{self.name}' and difficulty '{difficulty}'")

    @property
    def num_difficulties(self):
        return len(self.difficulties_single) + len(self.diffculties_double)

    def generate_leaderboards(self):
        count = 0
        for difficulty in self.difficulties_single:
            self.leaderboards[difficulty + " (Single)"] = Leaderboard(difficulty, "single")
            count = count + 1
        for difficulty in self.difficulties_double:
            self.leaderboards[difficulty + " (Double)"] = Leaderboard(difficulty, "double")
            count = count + 1
        return count

    def __str__(self):
        return f"{self.name} with difficulties {self.difficulties_single}"

### Course Classes ###
class Classification:
    def __init__(self, name):
        self.name = name
        self.packs = []

    def add_pack(self, pack):
        self.packs.append(pack)

    @property
    def num_packs(self):
        return len(self.packs)

    def __str__(self):
        return f"{self.name} containing {self.num_packs} packs"
    
class Pack:
    def __init__(self, name):
        self.name = name
        self.courses = []

    def add_course(self, course):
        self.courses.append(course)

    @property
    def num_courses(self):
        return len(self.courses)

    def __str__(self):
        return f"{self.name} containing {self.num_courses} courses"

class Course:
    def __init__(self, name):
        self.name = name
        self.difficulties_single = []
        self.difficulties_double = []
        self.leaderboards = {}

    def add_difficulty(self, difficulty, type):
        match type:
            case "single":
                if difficulty not in self.difficulties_single:
                    self.difficulties_single.append(difficulty)
            case "double":
                if difficulty not in self.difficulties_double:
                    self.difficulties_double.append(difficulty)
            case _:
                print(f"Unknown type '{type}' for course '{self.name}' and difficulty '{difficulty}'")

    @property
    def num_difficulties(self):
        return len(self.difficulties_single) + len(self.difficulties_double)

    def generate_leaderboards(self):
        count = 0
        for difficulty in self.difficulties_single:
            self.leaderboards[difficulty + " (Single)"] = Leaderboard(difficulty, "single")
            count = count + 1
        for difficulty in self.difficulties_double:
            self.leaderboards[difficulty + " (Double)"] = Leaderboard(difficulty, "double")
            count = count + 1
        return count

    def __str__(self):
        return f"{self.name} with difficulties {self.difficulties}"

### Universal Classes ###
class Leaderboard:
    def __init__(self, difficulty, type):
        self.difficulty = difficulty
        self.type = type
        self.entries = []

    def add_entry(self, someRecord):
        newEntry = Leaderboard_Entry(someRecord.inits, someRecord.percentage, someRecord.grade, someRecord.award, someRecord.date)
        self.entries.append(newEntry)

    @property
    def num_records(self):
        return len(self.entries)

    def sort(self):
        self.entries.sort(key=lambda x: (-x.percentage, x.date))

class Leaderboard_Entry:
    def __init__(self, inits, percentage, grade, award, date):
        self.inits = inits
        self.percentage = percentage
        self.grade = grade
        self.award = award
        self.date = date
        self.player = find_friendly_name(inits)

class Player_Song_Entry:
    def __init__(self, section, folder, song, difficulty, type, percentage, grade, award, date, position):
        self.section = section
        self.folder = folder
        self.song = song
        self.difficulty = difficulty
        self.type = type
        self.percentage = percentage
        self.grade = grade
        self.award = award
        self.date = date
        self.position = position

class Player_Course_Entry:
    def __init__(self, classification, pack, course, difficulty, type, percentage, grade, award, date, position):
        self.classification = classification
        self.pack = pack
        self.course = course
        self.difficulty = difficulty
        self.type = type
        self.percentage = percentage
        self.grade = grade
        self.award = award
        self.date = date
        self.position = position

class Player:
    def __init__(self, name):
        self.name = name
        self.inits = []
        self.songscores = []
        self.coursescores = []

    def add_song_score(self, score):
        self.songscores.append(score)

    def add_course_score(self, score):
        self.coursescores.append(score)

    def add_inits(self, inits):
        self.inits.append(inits)

    @property
    def total_scores(self):
        return len(self.songscores)

    @property
    def top_scores(self):
        tops = 0
        for score in self.songscores:
            if score.position == 1:
                tops = tops + 1
        return tops

    def __str__(self):
        return f"{self.name} ({self.inits}) with {self.total_scores} scores"

### Song XML Representers
def section_representer(dumper, data):
    return dumper.represent_dict ({
        "section_name": data.name,
        "folders":data.folders
    })

def folder_representer(dumper, data):
    return dumper.represent_dict ({
        "folder_name": data.name,
        "songs": data.songs 
    })

def song_representer(dumper, data):
    return dumper.represent_dict ({
        "song_title": data.name,
        "difficulties_single": data.difficulties_single,
        "difficulties_double": data.difficulties_double,
        "leaderboards": data.leaderboards
    })

### Course XML Representers ###
def classification_representer(dumper, data):
    return dumper.represent_dict ({
        "classification_name": data.name,
        "packs":data.packs
    })

def pack_representer(dumper, data):
    return dumper.represent_dict ({
        "pack_name": data.name,
        "courses": data.courses 
    })

def course_representer(dumper, data):
    return dumper.represent_dict ({
        "course_name": data.name,
        "difficulties_single": data.difficulties_single,
        "difficulties_double": data.difficulties_double,
        "leaderboards": data.leaderboards
    })

def player_representer(dumper, data):
    return dumper.represent_dict ({
        "player_name": data.name,
        "initials": data.inits,
        "total_scores": data.total_scores,
        "top_scores": data.top_scores,
        "song_scores": data.songscores,
        "course_scores": data.coursescores
    })

def leaderboard_representer(dumper, data):
    return dumper.represent_dict({
        "type": data.type,
        "entries": data.entries
    })

def leaderboard_entry_representer(dumper, data):
    return dumper.represent_dict({
        "player": data.player,
        "percentage": f"{data.percentage:.2f}",
        "grade": data.grade,
        "award": data.award,
        "date": data.date
    })

def player_song_entry_representer(dumper, data):
    return dumper.represent_dict({
        "section": data.section,
        "folder": data.folder,
        "song": data.song,
        "difficulty": data.difficulty,
        "type": data.type,
        "percentage": f"{data.percentage:.2f}",
        "grade": data.grade,
        "award": data.award,
        "date": data.date,
        "position": data.position 
    })

def player_course_entry_representer(dumper, data):
    return dumper.represent_dict({
        "classification": data.classification,
        "pack": data.pack,
        "course": data.course,
        "difficulty": data.difficulty,
        "type": data.type,
        "percentage": f"{data.percentage:.2f}",
        "grade": data.grade,
        "award": data.award,
        "date": data.date,
        "position": data.position 
    })

yaml.add_representer(Section, section_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Folder, folder_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Song, song_representer, Dumper=yaml.SafeDumper)

yaml.add_representer(Classification, classification_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Pack, pack_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Course, course_representer, Dumper=yaml.SafeDumper)

yaml.add_representer(Player, player_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Leaderboard, leaderboard_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Leaderboard_Entry, leaderboard_entry_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Player_Song_Entry, player_song_entry_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Player_Course_Entry, player_course_entry_representer, Dumper=yaml.SafeDumper)

def get_unique_machine_inits(score_data):
    unique_players = set()
    
    for XML_Entry in score_data:
        unique_players.add(XML_Entry.inits)
        
    return list(unique_players)

def find_friendly_name(player):
    with open(PLAYER_ALIASES, "r", encoding="utf-8") as f:
        file_data = yaml.safe_load(f)
        if isinstance(file_data, dict):
            friendlies = file_data

    return friendlies.get(player, player)

def generate_section_list():
    with open(SONG_FOLDER_WHITELIST, "r", encoding="utf-8") as f:
        whitelist_data = yaml.safe_load(f)

    count = 0
    section_list = []

    if isinstance(whitelist_data, dict):
        for section_name, whitelisted_folders in whitelist_data.items():
            new_section = Section(section_name)
            
            if isinstance(whitelisted_folders, list):
                for folder_name in whitelisted_folders:
                    # Append every folder directly from the whitelist file
                    new_section.add_folder(Folder(folder_name))
            
            new_section.folders.sort(key=sort_folders_by_mix, reverse=False)
            
            section_list.append(new_section)
            count = count + 1
                
    return section_list

def generate_classification_list():
    with open(COURSE_PACK_WHITELIST, "r", encoding="utf-8") as f:
        whitelist_data = yaml.safe_load(f)

    count = 0
    classification_list = []

    if isinstance(whitelist_data, dict):
        for classification_name, whitelisted_packs in whitelist_data.items():
            new_classification = Classification(classification_name)

            if isinstance(whitelisted_packs, list):
                for pack_name in whitelisted_packs:
                    new_pack = Pack(pack_name)
                    new_classification.add_pack(new_pack)

            new_classification.packs.sort(key=lambda pack: pack.name)

            classification_list.append(new_classification)
            count = count + 1

    return classification_list

def generate_folder_list(scores):
    unique_folders = set()

    for score in scores:
        unique_folders.add(score.folder)

    unique_folder_list = []

    for folder in unique_folders:
        unique_folder_list.append(Folder(folder))

    return unique_folder_list

def generate_pack_list(scores):
    unique_packs = set()

    for score in scores:
        unique_packs.add(score.pack)

    unique_pack_list = []

    for pack in unique_packs:
        unique_pack_list.append(Pack(pack))

    return unique_pack_list

def extract_folder_list(section_list):
    folder_list = []
    
    for section in section_list:
        for folder in section.folders:
            folder_list.append(folder)

    return folder_list

def extract_pack_list(classification_list):
    pack_list = []
    
    for classification in classification_list:
        for pack in classification.packs:
            pack_list.append(pack)

    return pack_list

def generate_song_list(score_data):
    unique_songs = set()

    for song_entry in score_data:
        unique_songs.add(song_entry.song)

    unique_song_list = []

    for song in unique_songs:
        unique_song_list.append(Song(song))

    return list (unique_song_list)

def generate_player_list(score_name_list):
    actually_unique_players = []

    for score_name in score_name_list:
        friendly_name = find_friendly_name(score_name)

        if len(actually_unique_players) == 0:
            new_player = Player(friendly_name)
            new_player.add_inits(score_name)
            actually_unique_players.append(new_player)

        else:
            existing = False
            for actually_unique_player in actually_unique_players:
                if actually_unique_player.name == friendly_name:
                    actually_unique_player.add_inits(score_name)
                    existing = True

            if existing == False:
                new_player = Player(friendly_name)
                new_player.add_inits(score_name)
                actually_unique_players.append(new_player)   

    return actually_unique_players

def associate_player_scores(XML_scores, player_list):
    associations = 0
    checks = 0

    for xml_score in XML_scores:
        matching_player = next((player for player in player_list if xml_score.inits in player.inits), None)
        matching_player.add_score(xml_score)
        associations = associations + 1

    return associations

def associate_songs_to_folders(score_list, folder_list):
    associations = 0
    for score in score_list:
        matching_folder = next((folder for folder in folder_list if folder.name == score.folder), None)
        if not matching_folder:
            continue

        matching_song = next((song for song in matching_folder.songs if song.name == score.song), None)

        if not matching_song:
            matching_folder.add_song(Song(score.song))
            associations = associations + 1

    return associations

def associate_courses_to_packs(score_list, pack_list):
    associations = 0
    for score in score_list:
        matching_pack = next((pack for pack in pack_list if pack.name == score.pack), None)
        if not matching_pack:
            continue

        matching_course = next((course for course in matching_pack.courses if course.name == score.course), None)

        if not matching_course:
            matching_pack.add_course(Course(score.course))
            associations = associations + 1

    return associations

def associate_difficulties_to_songs(score_list, folder_list):

    associations = 0
    for score in score_list:
        matching_folder = next((folder for folder in folder_list if folder.name == score.folder), None)
        if not matching_folder:
            continue

        matching_song = next((song for song in matching_folder.songs if song.name == score.song), None)
        if not matching_song:
            continue

        if score.type == "single":
            if score.difficulty not in matching_song.difficulties_single:
                matching_song.add_difficulty(score.difficulty, "single")
                associations = associations + 1

        if score.type == "double":
            if score.difficulty not in matching_song.difficulties_double:
                matching_song.add_difficulty(score.difficulty, "double")
                associations = associations + 1

    for folder in folder_list:
        for song in folder.songs:
            song.difficulties_single.sort(
                key=lambda difficulty: (
                    DIFFICULTY_ORDER.index(difficulty)
                    if difficulty in DIFFICULTY_ORDER
                    else len(DIFFICULTY_ORDER)
                )
            )
            song.difficulties_double.sort(
                key=lambda difficulty: (
                    DIFFICULTY_ORDER.index(difficulty)
                    if difficulty in DIFFICULTY_ORDER
                    else len(DIFFICULTY_ORDER)
                )
            )
    return associations

def associate_difficulties_to_courses(score_list, pack_list):

    associations = 0

    for score in score_list:
        matching_pack = next((pack for pack in pack_list if pack.name == score.pack), None)
        if not matching_pack:
            continue

        matching_course = next((course for course in matching_pack.courses if course.name == score.course), None)
        if not matching_course:
            continue

        if score.type == "single":
            if score.difficulty not in matching_course.difficulties_single:
                matching_course.add_difficulty(score.difficulty, "single")
                associations = associations + 1

        if score.type == "double":
            if score.difficulty not in matching_course.difficulties_double:
                matching_course.add_difficulty(score.difficulty, "double")
                associations = associations + 1

    for pack in pack_list:
        for course in pack.courses:
            course.difficulties_single.sort(
                key=lambda difficulty: (
                    DIFFICULTY_ORDER.index(difficulty)
                    if difficulty in DIFFICULTY_ORDER
                    else len(DIFFICULTY_ORDER)
                )
            )
            course.difficulties_double.sort(
                key=lambda difficulty: (
                    DIFFICULTY_ORDER.index(difficulty)
                    if difficulty in DIFFICULTY_ORDER
                    else len(DIFFICULTY_ORDER)
                )
            )

    return associations

def generate_song_leaderboards(folder_list):
    count = 0
    for folder in folder_list:
        for song in folder.songs:
            count = count + song.generate_leaderboards()

    return count

def generate_course_leaderboards(pack_list):
    count = 0
    for pack in pack_list:
        for course in pack.courses:
            count = count + course.generate_leaderboards()

    return count

def populate_song_leaderboards(score_data, folder_list):
    count = 0

    for score in score_data:
        matching_folder = next((f for f in folder_list if f.name == score.folder), None)
        if not matching_folder:
            continue
            
        matching_song = next((s for s in matching_folder.songs if s.name == score.song), None)
        if not matching_song:
            continue

        match score.type:
            case "single":
                score.difficulty = score.difficulty + " (Single)"
            case "double":
                score.difficulty = score.difficulty + " (Double)"
            case  _:
                print(f"Unknown type '{score.type}' for score '{score}'")

        leaderboard = matching_song.leaderboards.get(score.difficulty)
        
        if leaderboard:
            leaderboard.add_entry(score)
            count += 1

        else:
            print("Warning: leaderboard not found for " + str(score_data))


    for folder in folder_list:
        for song in folder.songs:
            for leaderboard in song.leaderboards.values():
                leaderboard.sort()

    return count

def populate_course_leaderboards(score_data, pack_list):
    count = 0

    for score in score_data:
        matching_pack = next((pack for pack in pack_list if pack.name == score.pack), None)
        if not matching_pack:
            continue

        matching_course = next((course for course in matching_pack.courses if course.name == score.course), None)
        if not matching_course:
            continue

        match score.type:
            case "single":
                score.difficulty = score.difficulty + " (Single)"
            case "double":
                score.difficulty = score.difficulty + " (Double)"
            case _:
                print(f"Unknown type '{score.type}' for score '{score}'")
                continue

        leaderboard = matching_course.leaderboards.get(score.difficulty)
        if leaderboard:
            leaderboard.add_entry(score)
            count += 1
        else:
            print(f"Warning: course leaderboard not found for {score}")

    for pack in pack_list:
        for course in pack.courses:
            for leaderboard in course.leaderboards.values():
                leaderboard.sort()

    return count

def populate_player_data(section_list, classification_list, player_list):
    count = 0
    
    for section in section_list:
        for folder in section.folders:
            for song in folder.songs:
                for leaderboard in song.leaderboards.values():
                    for index, entry in enumerate(leaderboard.entries, start=1):
                        matching_player = next((player for player in player_list if entry.inits in player.inits), None)
                        if matching_player:
                            matching_player.add_song_score(Player_Song_Entry(
                                section.name, 
                                folder.name, 
                                song.name, 
                                leaderboard.difficulty, 
                                leaderboard.type,
                                entry.percentage, 
                                entry.grade, 
                                entry.award, 
                                entry.date,
                                index
                            ))
                            count = count + 1

    for classification in classification_list:
        for pack in classification.packs:
            for course in pack.courses:
                for leaderboard in course.leaderboards.values():
                    for index, entry in enumerate(leaderboard.entries, start=1):
                        matching_player = next((player for player in player_list if entry.inits in player.inits), None)
                        if matching_player:
                            matching_player.add_course_score(Player_Course_Entry(
                                classification.name,
                                pack.name,
                                course.name,
                                leaderboard.difficulty,
                                leaderboard.type,
                                entry.percentage,
                                entry.grade,
                                entry.award,
                                entry.date,
                                index
                            ))
                            count = count + 1

    for player in player_list:
        player.songscores.sort(key=attrgetter("percentage", "song"), reverse=True)
        player.coursescores.sort(key=attrgetter("percentage", "course"), reverse=True)
    return count

#Shitty google method.  I just want 10th mix in the right place.
def sort_folders_by_mix(folder):
    name = folder.name
    
    # 1. Isolate the explicit integer value from the mix string
    match = re.search(r'(\d+)', name)
    # CHANGED: Fallback to 1 (the first game) if no number exists, instead of 999
    mix_number = int(match.group(1)) if match else 1
    
    # 2. Strip numbers and common ordinal suffixes (st, nd, rd, th)
    series_clean = re.sub(r'\d+(st|nd|rd|th)?', '', name, flags=re.IGNORECASE)
    series_clean = series_clean.lower().strip()
    
    # 3. Floating catch-all: Keep custom packs like "Unofficial" at the very bottom
    is_catchall = 1 if series_clean.startswith('un') else 0

    # Return the multi-layered evaluation coordinate tuple
    return (is_catchall, series_clean, mix_number, name)

### Fixups ###
# Removes all dates prior to when I got the ITG Machine.
def datefix(song_scores, course_scores):
    invalid = 0
    date_format = "%Y-%m-%d %H:%M:%S"

    for theScore in song_scores:
        dt = datetime.strptime(theScore.date, date_format)

        if dt.year < 2011:
            theScore.date = "Unknown Date"

            invalid = invalid + 1

    for theScore in course_scores:
        dt = datetime.strptime(theScore.date, date_format)
    
        if dt.year < 2011:
            theScore.date = "Unknown Date"

            invalid = invalid + 1
    return invalid

#Removes all scores from folders not in the whitelist.
def folder_purge(score_list):
    with open(SONG_FOLDER_WHITELIST, "r", encoding="utf-8") as f:
        whitelist_data = yaml.safe_load(f)
    
    allowed_folders = set()
    if isinstance(whitelist_data, dict):
        for category, folders in whitelist_data.items():
            if isinstance(folders, list):
                allowed_folders.update(folders)

    purged_scores = []

    for score in score_list:
        if score.folder in allowed_folders:
            purged_scores.append(score)

    return purged_scores

#Removes all scores from ITG2 that are not in the ITG2 whitelist.
def itg2_purge(score_list):
    with open(SONG_FOLDER_WHITELIST, "r", encoding="utf-8") as f:
        whitelist_data = yaml.safe_load(f)

    itg2_valid_songs = ITG2_WHITELIST.read_text(encoding="utf-8").splitlines()

    purged_scores = []
    purged_songs = set()

    for score in score_list:
        if score.folder == "In The Groove 2":
            if score.song in itg2_valid_songs:
                purged_scores.append (score)
            else:
                purged_songs.add(score.song)
        else:
            purged_scores.append (score)

    #Output purged songs to file
    with open(ITG2_BLACKLIST, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(purged_songs)))

    return purged_scores

def export_sections_to_yaml(section_list, filename=SONG_CATALOG):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(section_list, f, default_flow_style=False, sort_keys=False)
    print(f"Successfully exported nested song leaderboards to {filename}")

def export_classifications_to_yaml(classification_list, filename=COURSE_CATALOG):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(classification_list, f, default_flow_style=False, sort_keys=False)
    print(f"Successfully exported nested course leaderboards to {filename}")

def export_players_to_yaml(section_list, filename=PLAYERS):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(section_list, f, default_flow_style=False, sort_keys=False)
    print(f"Successfully exported player data to {filename}")

def deduplicate_leaderboard_entries(section_list, classification_list):
    removed_count = 0

    def deduplicate(leaderboard):
        nonlocal removed_count
        seen_players = set()
        unique_entries = []

        for entry in leaderboard.entries:
            if entry.player in seen_players:
                removed_count += 1
                continue

            seen_players.add(entry.player)
            unique_entries.append(entry)

        leaderboard.entries = unique_entries

    for section in section_list:
        for folder in section.folders:
            for song in folder.songs:
                for leaderboard in song.leaderboards.values():
                    deduplicate(leaderboard)

    for classification in classification_list:
        for pack in classification.packs:
            for course in pack.courses:
                for leaderboard in course.leaderboards.values():
                    deduplicate(leaderboard)

    return removed_count

def main():
    # Parse the stats.xml data
    tree = ET.parse(SCRIPT_DIR / "Input" / "Stats.xml")
    root = tree.getroot()

    xml_song_score_data = []
    xml_course_score_data = []
    score_counter = 0

    for song in root.findall('.//Song'):
        dir_path = song.get('Dir')
        song_folder = dir_path.split('/')[-3] if dir_path else "Unknown Folder"
        song_title = dir_path.split('/')[-2] if dir_path else "Unknown Song"
        
        for steps in song.findall('.//Steps'):
            difficulty = steps.get('Difficulty')
            type = steps.get('StepsType').split("-")[1]
            
            for high_score in steps.findall('.//HighScoreList/HighScore'):
                score_counter = score_counter + 1
                pct_steps = high_score.find('PercentDP')
                score = float(pct_steps.text) * 100 if pct_steps is not None else 0.0
                player_name = high_score.find('Name').text if high_score.find('Name') is not None else "Unknown Player"
                grade = high_score.find('Grade').text if high_score.find('Grade') is not None else "No Grade"
                date = high_score.find('DateTime').text if high_score.find('DateTime') is not None else "Unknown Date"
                award = high_score.find('StageAward').text if high_score.find('StageAward') is not None else "No Award"

                if grade != "Failed" and score > 0 and player_name != None:
                    xml_song_score_data.append(XML_Song_Record(player_name, song_folder, song_title, difficulty, type, score, grade, award, date))

    for course in root.findall('.//Course'):
        dir_path = course.get('Path')
        course_path = dir_path.split('/') if dir_path else []
        course_pack = course_path[-2] if len(course_path) >= 2 else "Unknown Pack"
        course_title = Path(course_path[-1]).stem if course_path else "Unknown Course"

        for trail in course.findall('.//Trail'):
            difficulty = trail.get('CourseDifficulty')
            type = trail.get('StepsType').split("-")[1]

            for high_score in trail.findall('.//HighScoreList/HighScore'):
                score_counter = score_counter + 1
                pct_steps = high_score.find('PercentDP')
                score = float(pct_steps.text) * 100 if pct_steps is not None else 0.0
                player_name = high_score.find('Name').text if high_score.find('Name') is not None else "Unknown Player"
                grade = high_score.find('Grade').text if high_score.find('Grade') is not None else "No Grade"
                date = high_score.find('DateTime').text if high_score.find('DateTime') is not None else "Unknown Date"
                award = high_score.find('StageAward').text if high_score.find('StageAward') is not None else "No Award"

                if grade != "Failed" and score > 0 and player_name != None:
                    xml_course_score_data.append(XML_Course_Record(player_name, course_pack, course_title, difficulty, type, score, grade, award, date))

    print("Evaluated " + str(score_counter) + " score entries.")
    print("Successfully discovered " + str(len(xml_song_score_data)) + " passing song scores with names!")
    print("Successfully discovered " + str(len(xml_course_score_data)) + " passing course scores with names!")

    xml_song_score_data = folder_purge(xml_song_score_data)
    print("Reduced song scores to " + str(len(xml_song_score_data)) + " scores in whitelisted folders.")

    xml_song_score_data = itg2_purge(xml_song_score_data)
    print("Reduced song scores to " + str(len(xml_song_score_data)) + " scores from invalid ITG2 song records.")

    print("Marked " + str(datefix(xml_song_score_data, xml_course_score_data)) + " dates older than 2011 as invalid.")

    section_list = generate_section_list()
    folder_list = extract_folder_list(section_list)

    folder_list.sort(key=sort_folders_by_mix, reverse=False)
    print("Successfully identified " + str(len(folder_list)) + " unique folders.")
    
    classification_list = generate_classification_list()
    pack_list = extract_pack_list(classification_list)

    pack_list.sort(key=lambda pack: pack.name, reverse=False)
    print("Successfully identified " + str(len(pack_list)) + " unique packs.")

    machine_player_list = get_unique_machine_inits(xml_song_score_data)
    print("Successfully discovered " + str(len(machine_player_list)) + " unique name entries.")

    player_list = generate_player_list(machine_player_list)
    print("Merged down to " + str(len(player_list)) + " unique human players.")

    count_songs_associated = associate_songs_to_folders(xml_song_score_data, folder_list)
    print("Associated " + str(count_songs_associated) + " songs to parent folders.")

    count_courses_associated = associate_courses_to_packs(xml_course_score_data, pack_list)
    print("Associated " + str(count_courses_associated) + " courses to parent packs.")

    count_song_difficulties_associated = associate_difficulties_to_songs(xml_song_score_data, folder_list)
    print("Associated " + str(count_song_difficulties_associated) + " difficulties to parent songs.")

    count_course_difficulties_associated = associate_difficulties_to_courses(xml_course_score_data, pack_list)
    print("Associated " + str(count_course_difficulties_associated) + " difficulties to parent courses.")

    count_song_leaderboards_generated = generate_song_leaderboards(folder_list)
    print("Created " + str(count_song_leaderboards_generated) + " empty leaderboards")

    count_course_leaderboards_generated = generate_course_leaderboards(pack_list)
    print("Created " + str(count_course_leaderboards_generated) + " empty course leaderboards")

    count_song_populations = populate_song_leaderboards(xml_song_score_data, folder_list)
    print("Added " + str(count_song_populations) + " XML scores to " + str(count_song_leaderboards_generated) + " leaderboards.")

    count_course_populations = populate_course_leaderboards(xml_course_score_data, pack_list)
    print("Added " + str(count_course_populations) + " XML scores to " + str(count_course_leaderboards_generated) + " course leaderboards.")

    duplicate_entries_removed = deduplicate_leaderboard_entries(section_list, classification_list)
    print("Removed " + str(duplicate_entries_removed) + " duplicate player entries from leaderboards.")

    count_player_scores_associated = populate_player_data(section_list, classification_list, player_list)
    print("Associated " + str(count_player_scores_associated) + " scores to player profiles.")
    player_list.sort(key=attrgetter('top_scores', 'name'), reverse=True)
    
    export_sections_to_yaml(section_list, filename=SONG_CATALOG)
    export_classifications_to_yaml(classification_list, filename=COURSE_CATALOG)
    export_players_to_yaml(player_list)

    html_generator.generate_html_with_jinja()

if __name__ == "__main__":
    main()