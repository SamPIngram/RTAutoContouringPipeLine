import logging
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from backend.core.base_trigger import BaseTrigger

logger = logging.getLogger(__name__)

DICOM_EXTENSIONS = {".dcm", ".DCM", ".ima", ".IMA"}


class _DicomHandler(FileSystemEventHandler):
    def __init__(self, callback) -> None:
        self._callback = callback

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).suffix in DICOM_EXTENSIONS:
            logger.debug("New DICOM file detected", extra={"path": event.src_path})
            self._callback(event.src_path)


class FolderWatcher(BaseTrigger):
    """Monitors a directory for new DICOM files and enqueues conversion tasks."""

    def __init__(self, watch_path: str, recursive: bool = True) -> None:
        self._watch_path = watch_path
        self._recursive = recursive
        self._observer: Observer | None = None

    @property
    def trigger_type(self) -> str:
        return "folder_watch"

    def listen(self) -> None:
        from backend.tasks.conversion import convert_dicom_to_nifti

        def _on_new_file(path: str) -> None:
            convert_dicom_to_nifti.delay(
                folder_path=str(Path(path).parent),
                recursive=False,
                import_source="folder_watch",
            )

        handler = _DicomHandler(callback=_on_new_file)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_path, recursive=self._recursive)
        self._observer.start()
        logger.info("Folder watcher started", extra={"path": self._watch_path})

        try:
            self._observer.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            logger.info("Folder watcher stopped")
