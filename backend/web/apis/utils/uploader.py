"""Image/video storage. Pillow (lazy) is used for resizing; no OpenCV/numpy dependency."""
import logging
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

log = logging.getLogger("web")
IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


class Uploader:
    def _folder(self):
        folder = os.path.join(current_app.root_path, current_app.config["MEDIA_LOCATION"])
        os.makedirs(folder, exist_ok=True)
        return folder

    def public_url(self, filename):
        base = current_app.config.get("API_PUBLIC_URL", "")
        return f"{base}/{current_app.config['MEDIA_LOCATION'].strip('/')}/{filename}"

    def save(self, file_storage):
        """Store an uploaded file; returns ``(public_url, local_path)``."""
        original = secure_filename(file_storage.filename or "")
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
            raise ValueError("Unsupported file type.")
        filename = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(self._folder(), filename)
        file_storage.save(path)
        if ext in IMAGE_EXT:
            self._shrink(path)
        return self.public_url(filename), path

    @staticmethod
    def _shrink(path):
        try:
            from PIL import Image

            limit = current_app.config["IMAGE_MAX_DIMENSION"]
            with Image.open(path) as img:
                if max(img.size) > limit and getattr(img, "n_frames", 1) == 1:
                    img.thumbnail((limit, limit))
                    img.save(path, optimize=True, quality=85)
        except Exception:  # noqa: BLE001 - keep the original file if resizing is impossible
            log.warning("Could not resize %s; stored as uploaded.", path)

    def delete_local(self, url):
        name = os.path.basename(str(url or "").split("?")[0])
        target = os.path.join(self._folder(), name)
        if name and os.path.isfile(target):
            os.remove(target)


uploader = Uploader()
