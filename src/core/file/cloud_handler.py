from typing import Protocol


class CloudHandler(Protocol):

    def set_credentials(self, credentials): ...

    @property
    def service_client(self): ...

    @property
    def default_container(self): ...

    def upload_blob_file(
        self,
        file_path: str,
        destination_name: str | None = None,
        container_name: str | None = None,
        overwrite=True,
    ):
        """Upload local file to Cloud Blob storage

        Args:
            file_path (str): The full path to file.
            destination_name (str, optional): The destination path to upload to. Defaults to file name of source file.
            container_name (str, optional): The container/bucket to upload to. Will use default container if not provide.
            overwrite (bool, optional): Overwrite the file or not. Defaults to True.
        """

    def download_blob_file(
        self,
        blob_path: str,
        destination_path: str | None = None,
        container_name: str | None = None,
    ):
        """Download a blob file from Cloud Blob storage

        Args:
            blob_path (str): The path to the blob file in the cloud.
            destination_path (str, optional): The local path to save the downloaded file. Defaults to the current working directory with the same name as the blob.
            container_name (str, optional): The container/bucket to download from. Will use the default container if not provided.
        Returns:
            str: The full path to the downloaded file.
        """


class DummyCloudHandler(CloudHandler):
    def __init__(self) -> None:
        pass

    def set_credentials(self, credentials):
        print("Setting credentials")
        print(f"Credentials: {credentials}")
        print("Credentials set!")

    @property
    def service_client(self):
        pass

    @property
    def default_container(self):
        pass

    def upload_blob_file(
        self,
        file_path: str,
        destination_name: str | None = None,
        container_name: str | None = None,
        overwrite=True,
    ):
        print(f"Uploading {file_path} to {container_name}/{destination_name}")
        print(f"Overwrite: {overwrite}")
        print("Upload complete!")

    def download_blob_file(
        self,
        blob_path: str,
        destination_path: str | None = None,
        container_name: str | None = None,
    ):
        print(f"Downloading {blob_path} from {container_name}")
        print(f"Saving to {destination_path}")
        print("Download complete!")