from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
VOICE_DIR = ROOT / "models" / "voices"
INDEX_DIR = ROOT / "models" / "indices"
OUTPUT_DIR = ROOT / "outputs"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
JOB_DB_PATH = DATA_DIR / "jobs.sqlite3"
RVC_ROOT = ROOT / "vendor" / "rvc"
