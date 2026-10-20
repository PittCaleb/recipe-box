import os
import platform
from pathlib import Path


def _default_share_backend():
    return "mac" if platform.system() == "Darwin" else "none"


class Config:
    DATA_DIR = Path(os.environ.get("RECIPES_DATA_DIR", "./data")).resolve()
    HOST = os.environ.get("RECIPES_HOST", "0.0.0.0")
    PORT = int(os.environ.get("RECIPES_PORT", "5050"))
    SHARE_BACKEND = os.environ.get("RECIPES_SHARE_BACKEND", _default_share_backend())
    APP_PASSWORD = os.environ.get("RECIPES_APP_PASSWORD") or None
    COOKBOOK_TITLE = os.environ.get("RECIPES_COOKBOOK_TITLE", "Our Family Recipes")

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
