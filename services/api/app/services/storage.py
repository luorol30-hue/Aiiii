import mimetypes
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import ExternalServiceUnavailable


class ObjectStorage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=str(settings.s3_endpoint_url) if settings.s3_endpoint_url else None,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def upload_leaf_image(self, file: UploadFile, user_id: str) -> str:
        extension = mimetypes.guess_extension(file.content_type or "") or ".jpg"
        key = f"leaf-images/{user_id}/{uuid.uuid4()}{extension}"
        try:
            file.file.seek(0)
            self.client.upload_fileobj(
                file.file,
                self.settings.s3_bucket,
                key,
                ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
            )
            file.file.seek(0)
        except (BotoCoreError, ClientError) as exc:
            raise ExternalServiceUnavailable("Object storage upload failed") from exc

        if self.settings.s3_public_base_url:
            return f"{str(self.settings.s3_public_base_url).rstrip('/')}/{key}"
        return f"s3://{self.settings.s3_bucket}/{key}"
