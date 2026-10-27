import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file next to this one, if present. Real
# environment variables (e.g. set by Docker, launchd, or your shell) always
# win -- load_dotenv() never overrides a variable that's already set.
load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    DATA_DIR = Path(os.environ.get("RECIPES_DATA_DIR", "./data")).resolve()
    HOST = os.environ.get("RECIPES_HOST", "0.0.0.0")
    PORT = int(os.environ.get("RECIPES_PORT", "5050"))
    # Sign-in through Cloudflare Access (see app/users.py). The team domain is
    # e.g. "yourteam.cloudflareaccess.com"; the AUD is the Access
    # application's "Application Audience (AUD) Tag".
    ACCESS_TEAM_DOMAIN = os.environ.get("RECIPES_ACCESS_TEAM_DOMAIN") or None
    ACCESS_AUD = os.environ.get("RECIPES_ACCESS_AUD") or None
    # Hostnames with no sign-in, where everyone acts as the owner (user 1).
    HOME_HOSTS = {
        h.strip().lower()
        for h in os.environ.get("RECIPES_HOME_HOSTS", "localhost,127.0.0.1").split(",")
        if h.strip()
    }
    COOKBOOK_TITLE = os.environ.get("RECIPES_COOKBOOK_TITLE", "Our Family Recipes")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or None
    IMPORT_MODEL = os.environ.get("RECIPES_IMPORT_MODEL", "claude-opus-5-5")
    PDF_DIR = Path(
        os.environ.get("RECIPES_PDF_DIR", str(Path(__file__).resolve().parent / "pdf"))
    ).resolve()

    @property
    def DB_PATH(self):
        return self.DATA_DIR / "recipes.db"

    @property
    def IMAGES_DIR(self):
        return self.DATA_DIR / "images"

    @property
    def SCANS_DIR(self):
        return self.DATA_DIR / "scans"

    @property
    def EXPORTS_DIR(self):
        return self.DATA_DIR / "exports"

    @property
    def TMP_DIR(self):
        return self.DATA_DIR / "tmp"

    @property
    def IMPORT_DIR(self):
        return self.DATA_DIR / "import"

    def ensure_data_dirs(self):
        for d in (self.DATA_DIR, self.IMAGES_DIR, self.SCANS_DIR, self.EXPORTS_DIR, self.TMP_DIR, self.IMPORT_DIR):
            d.mkdir(parents=True, exist_ok=True)


config = Config()
