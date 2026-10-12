"""Миниатюры и заглушка; вызывается только из главного потока Tkinter."""

from pathlib import Path

from PIL import Image, ImageTk, UnidentifiedImageError

PROJECT_DIR = Path(__file__).resolve().parents[1]


class ImageCache:
    def __init__(self, master):
        self.master = master
        self.cache = {}

    def get(self, relative_path: str | None, size: tuple[int, int]):
        key = (relative_path, size)
        if key not in self.cache:
            image = self._read(relative_path, size)
            if image is None and relative_path != "assets/picture.png":
                image = self.get("assets/picture.png", size)
            # Ссылка в кэше сохраняет PhotoImage от удаления сборщиком мусора.
            self.cache[key] = image
        return self.cache[key]

    def _read(self, relative_path, size):
        if not relative_path:
            return None
        path = (PROJECT_DIR / relative_path).resolve()
        if not path.is_relative_to(PROJECT_DIR):
            return None
        try:
            with Image.open(path) as source:
                source.thumbnail(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(source.convert("RGBA"), master=self.master)
        except (OSError, UnidentifiedImageError, ValueError):
            return None

    def clear(self):
        self.cache.clear()
