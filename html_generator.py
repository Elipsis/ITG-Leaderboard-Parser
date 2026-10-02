import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Directories
SCRIPT_DIR = Path(__file__).resolve().parent
CATALOG_PATH = SCRIPT_DIR / "Output" / "Leaderboard Tree.yaml"
PLAYERS_PATH = SCRIPT_DIR / "Output" / "Player Data.yaml"
OUTPUT_HTML = SCRIPT_DIR / "Output" / "Leaderboard.html"

def load_yaml_data():
    """Loads compiled databases directly from your output files."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    with open(PLAYERS_PATH, "r", encoding="utf-8") as f:
        players = yaml.safe_load(f)
    return catalog, players

def generate_html_with_jinja():
    catalog, players = load_yaml_data()
    
    # Configure Jinja environments to read your templates folder
    file_loader = FileSystemLoader(SCRIPT_DIR / "Input")
    env = Environment(loader=file_loader)
    
    # Load and compile the blueprint file
    template = env.get_template("template.html")
    
    # Pass data directly down to the Jinja template rendering scope
    rendered_output = template.render(catalog=catalog, players=players)
    
    # Export completed build to disk
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(rendered_output)
        
    print(f"Successfully generated clean Jinja2 leaderboard view to: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_html_with_jinja()
