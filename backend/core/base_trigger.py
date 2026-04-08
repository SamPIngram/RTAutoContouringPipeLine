from abc import ABC, abstractmethod


class BaseTrigger(ABC):
    """Base class for all pipeline triggers.

    Subclasses implement specific trigger mechanisms:
    - OrthancWebhookTrigger (orthanc_new_study)
    - FolderWatchTrigger (folder_watch)
    - ApiTrigger (api — manual/programmatic)
    """

    @abstractmethod
    def listen(self) -> None:
        """Start listening for trigger events. Blocks until stop() is called."""

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and clean up resources."""

    @property
    def trigger_type(self) -> str:
        raise NotImplementedError
