import base64
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
        self.has_s3 = bool(
            settings.s3_bucket and settings.s3_access_key_id and settings.s3_secret_access_key
        )
        if self.has_s3:
            self.client = boto3.client(
                "s3",
                region_name=settings.s3_region,
                endpoint_url=str(settings.s3_endpoint_url) if settings.s3_endpoint_url else None,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
            )

    def upload_leaf_image(self, file: UploadFile, user_id: str) -> str:
        if not self.has_s3:
            # Fallback to Data URI so scanning works immediately without requiring S3 setup
            file.file.seek(0)
            raw_bytes = file.file.read()
            file.file.seek(0)
            mime = file.content_type or "image/jpeg"
            b64_data = base64.b64encode(raw_bytes).decode("utf-8")
            return f"data:{mime};base64,{b64_data}"

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
