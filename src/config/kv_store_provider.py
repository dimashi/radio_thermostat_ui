import logging
from typing import Any, Type
from google.cloud import datastore
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

logger = logging.getLogger(__name__)

class FirestoreSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: Type[BaseSettings], collection: str, doc_id: str):
        super().__init__(settings_cls)
        self.collection = collection
        self.doc_id = doc_id

    def __call__(self) -> dict[str, Any]:
        try:
            # Initialize client and fetch data inside the try block
            db = datastore.Client()
            key = db.key(self.collection, self.doc_id)
            data = db.get(key)
            return dict(data) if data else {}

        except (DefaultCredentialsError, GoogleAPIError, Exception) as e:
            # Log a warning and safely fall back
            logger.warning(
                f"⚠️ Firestore config unreachable ({e}). Falling back to local sources."
            )
            return {}