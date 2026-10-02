import xml.etree.ElementTree as ET
import pandas as pd
import yaml
import html_generator
from operator import attrgetter
from datetime import datetime
from pathlib import Path

#Directory
SCRIPT_DIR = Path(__file__).resolve().parent

#INPUTS
SONG_WHITELIST = SCRIPT_DIR / "Input" / "Song Folder Whitelist.txt"
PLAYER_ALIASES = SCRIPT_DIR / "Input" / "Profile Initials.yaml"

#OUTPUTS
CATALOG = SCRIPT_DIR / "Output" / "Leaderboard Tree.yaml"
PLAYERS = SCRIPT_DIR / "Output" / "Player Data.yaml"

class XML_Record:
    def __init__(self, inits, folder, song, difficulty, percentage, grade, date):
        self.inits = inits
        self.folder = folder
        self.song = song
        self.difficulty = difficulty
        self.percentage = percentage
        self.grade = grade
        self.date = date

    def __str__(self):
        return f"{self.song} - ({self.difficulty}): {self.percentage} by {self.inits}"

class Song:
    def __init__(self, name):
        self.name = name
        self.difficulties = []
        self.leaderboards = {}

    def add_difficulty(self, difficulty):
        self.difficulties.append(difficulty)

    @property
    def num_difficulties(self):
        return len(self.difficulties)

    def generate_leaderboards(self):
        count = 0
        for difficulty in self.difficulties:
            self.leaderboards[difficulty] = Leaderboard(difficulty)
            count = count + 1
        return count

    def __str__(self):
        return f"{self.name} with difficulties {self.difficulties}"

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

class Leaderboard:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.entries = []

    def add_entry(self, someRecord):
        newEntry = Entry(someRecord.inits, someRecord.percentage, someRecord.grade, someRecord.date)
        self.entries.append(newEntry)

    @property
    def num_records(self):
        return len(self.entries)

    def sort(self):
        self.entries.sort(key=attrgetter('percentage', 'date'), reverse=True)

class Entry:
    def __init__(self, inits, percentage, grade, date):
        self.inits = inits
        self.percentage = percentage
        self.grade = grade
        self.date = date
        self.player = find_friendly_name(inits)

class Player:
    def __init__(self, name):
        self.name = name
        self.inits = []
        self.scores = []

    def add_score(self, score):
        self.scores.append(score)

    def add_inits(self, inits):
        self.inits.append(inits)

    @property
    def total_scores(self):
        return len(self.scores)

    def __str__(self):
        return f"{self.name} ({self.inits}) with {self.total_scores} scores"

def folder_representer(dumper, data):
    return dumper.represent_dict ({
        "folder_name": data.name,
        "songs": data.songs 
    })

def song_representer(dumper, data):
    return dumper.represent_dict ({
        "song_title": data.name,
        "difficulties": data.difficulties,
        "leaderboards": data.leaderboards
    })

def player_representer(dumper, data):
    return dumper.represent_dict ({
        "player_name": data.name,
        "initials": data.inits
    })

def leaderboard_representer(dumper, data):
    return dumper.represent_list(data.entries)

def entry_representer(dumper, data):
    return dumper.represent_dict({
        "player": data.player,
        "percentage": round(data.percentage, 2),  # Rounds to clean up floats
        "grade": data.grade,
        "date": data.date
    })

yaml.add_representer(Folder, folder_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Song, song_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Player, player_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Leaderboard, leaderboard_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(Entry, entry_representer, Dumper=yaml.SafeDumper)

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

def generate_folder_list(scores):
    unique_folders = set()

    for score in scores:
        unique_folders.add(score.folder)

    unique_folder_list = []

    for folder in unique_folders:
        unique_folder_list.append(Folder(folder))

    return (unique_folder_list)

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


def associate_songs_to_folders(score_list, folder_list, song_list):

    associations = 0
    for score in score_list:
        matching_folder = next((folder for folder in folder_list if folder.name == score.folder), None)
        matching_song = next((song for song in song_list if song.name == score.song), None)

        if matching_song not in matching_folder.songs:
            matching_folder.add_song(matching_song)
            associations = associations + 1

    return associations

def associate_difficulties_to_songs(score_list, song_list):

    associations = 0
    for score in score_list:
        matching_song = next((song for song in song_list if song.name == score.song), None)

        if score.difficulty not in matching_song.difficulties:
            matching_song.add_difficulty(score.difficulty)
            associations = associations + 1

    return associations

def generate_leaderboards(song_list):
    count = 0
    for song in song_list:
        count = count + song.generate_leaderboards()

    return count

def populate_leaderboards(score_data, folder_list):
    count = 0

    for score in score_data:
        matching_folder = next((f for f in folder_list if f.name == score.folder), None)
        if not matching_folder:
            continue
            
        matching_song = next((s for s in matching_folder.songs if s.name == score.song), None)
        if not matching_song:
            continue

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

def datefix(scores):
    invalid = 0
    date_format = "%Y-%m-%d %H:%M:%S"

    for theScore in scores:
        dt = datetime.strptime(theScore.date, date_format)
    
        # 2. Check if the year is older than 2011
        if dt.year < 2011:
            # Keep the same month and day, but force 2011 and midnight
            # dt = dt.replace(year=2011, hour=0, minute=0, second=0)
            theScore.date = "Unknown Date"

            invalid = invalid + 1
    return invalid

def whitelist_purge(score_list):
    # Open the whitelist file and read every line into a list
    with open(SONG_WHITELIST, "r", encoding="utf-8") as f:
        song_whitelist = f.read().splitlines()

    purged_scores = []

    for score in score_list:
        if score.folder in song_whitelist:
            purged_scores.append(score)

    return purged_scores


def export_folders_to_yaml(folder_list, filename=CATALOG):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(folder_list, f, default_flow_style=False, sort_keys=False)
    print(f"Successfully exported nested library to {filename}")

def export_players_to_yaml(folder_list, filename=PLAYERS):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(folder_list, f, default_flow_style=False, sort_keys=False)
    print(f"Successfully exported nested library to {filename}")


def main():
    # Parse the stats.xml data
    tree = ET.parse(SCRIPT_DIR / "Input" / "Stats.xml")
    root = tree.getroot()

    xml_score_data = []
    score_counter = 0

    for song in root.findall('.//Song'):
        dir_path = song.get('Dir')
        song_folder = dir_path.split('/')[-3] if dir_path else "Unknown Folder"
        song_title = dir_path.split('/')[-2] if dir_path else "Unknown Song"
        
        for steps in song.findall('.//Steps'):
            difficulty = steps.get('Difficulty')
            
            for high_score in steps.findall('.//HighScoreList/HighScore'):
                score_counter = score_counter + 1
                pct_steps = high_score.find('PercentDP')
                score = float(pct_steps.text) * 100 if pct_steps is not None else 0.0
                player_name = high_score.find('Name').text if high_score.find('Name') is not None else "Unknown Player"
                grade = high_score.find('Grade').text if high_score.find('Grade') is not None else "No Grade"
                date = high_score.find('DateTime').text if high_score.find('DateTime') is not None else "Unknown Date"

                if grade != "Failed" and score > 0 and player_name != None:
                    xml_score_data.append(XML_Record(player_name, song_folder, song_title, difficulty, score, grade, date))

    print("Evaluated " + str(score_counter) + " score entries.")
    print("Successfully discovered " + str(len(xml_score_data)) + " passing scores with names!")

    xml_score_data = whitelist_purge(xml_score_data)
    print("Reduced scores to " + str(len(xml_score_data)) + " scores in whitelisted folders.")

    print("Marked " + str(datefix(xml_score_data)) + " dates older than 2011 as invalid.")

    folder_list = generate_folder_list(xml_score_data)
    folder_list.sort(key=attrgetter('name'), reverse=False)
    print("Successfully identified " + str(len(folder_list)) + " unique folders.")

    song_list = generate_song_list(xml_score_data)
    song_list.sort(key=attrgetter('name'), reverse=False)
    print("Successfully identified " + str(len(song_list)) + " unique songs.")

    machine_player_list = get_unique_machine_inits(xml_score_data)
    print("Successfully discovered " + str(len(machine_player_list)) + " unique name entries.")

    player_list = generate_player_list(machine_player_list)
    print("Merged down to " + str(len(player_list)) + " unique human players.")

    count_player_scores_associated = associate_player_scores(xml_score_data, player_list)
    player_list.sort(key=attrgetter('total_scores', 'name'), reverse=True)
    print("Associated " + str(count_player_scores_associated) + " scores to player profiles.")
    
    count_songs_associated = associate_songs_to_folders(xml_score_data, folder_list, song_list)
    print("Associated " + str(count_songs_associated) + " songs to parent folders.")

    count_difficulties_associated = associate_difficulties_to_songs(xml_score_data, song_list)
    print("Associated " + str(count_difficulties_associated) + " difficulties to parent songs.")

    count_leaderboards_generated = generate_leaderboards(song_list)
    print("Created " + str(count_leaderboards_generated) + " empty leaderboards")

    count_populations = populate_leaderboards(xml_score_data, folder_list)
    print("Added " + str(count_populations) + " XML scores to " + str(count_leaderboards_generated) + " leaderboards.")

#    for player in player_list:
#        print(player)

    #toppest = sorted(score_data, key=attrgetter('percentage', 'date'), reverse=True)
    #oldest = sorted(score_data, key=attrgetter('date'), reverse=False)

    #print ("Top Score: " + str(toppest[0]))
    #print ("Bottom Score: " + str(toppest[-1]))
 #   print ("Oldest Score: " + str(oldest [0]))
 #   print ("Newest Score: " + str(oldest [-1]))

    export_folders_to_yaml(folder_list)
    export_players_to_yaml(player_list)

    html_generator.generate_html_with_jinja()

if __name__ == "__main__":
    main()