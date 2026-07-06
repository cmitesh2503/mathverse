from google.cloud import storage


class DocumentLoader:

    def __init__(self):

        self.client = storage.Client()

    def load_pdf(
        self,
        bucket_name: str,
        blob_name: str
    ) -> bytes:

        bucket = self.client.bucket(
            bucket_name
        )

        blob = bucket.blob(
            blob_name
        )

        if not blob.exists():

            raise FileNotFoundError(
                f"{blob_name} not found."
            )

        return blob.download_as_bytes()