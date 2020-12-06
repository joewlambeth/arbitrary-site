import os
import os.path
import zlib
import base64
from google.oauth2 import service_account
from google.cloud import storage
from flask import current_app


class FileHandler():
    def __init__(self, destination):
        self.destination = destination

    def save(self, filename, bytes):
        raise NotImplementedError("FileHandler is abstract: no behavior for 'save()'")

    def load(self, filename):
        raise NotImplementedError("FileHandler is abstract: no behavior for 'load()'")

    def delete(self, filename):
        raise NotImplementedError("FileHandler is abstract: no behavior for 'delete()'")



class LocalFileHandler(FileHandler):
    def save(self, filename, bytes):
        f = open(os.path.join(self.destination, filename), "wb" )
        f.write(bytes)
        f.close()

    def load(self, filename):
        f = open(os.path.join(self.destination, filename), "rb")
        bytes = f.read()
        f.close()
        return bytes

    def delete(self, filename):
        os.remove(filename)

class GCloudFileHandler(FileHandler):
    # in this case, self.destination serves as bucket name

    def __init__(self, destination):
        self.destination = destination
        credential_file = current_app.config["FS"].get("CREDENTIALS")
        if not credential_file:
            credentials = None
        else:
            credentials = service_account.Credentials.from_service_account_file(credential_file)
        self.client = storage.Client(credentials=credentials)

    def save(self, filename, bytes):
        blob = self.client.bucket(self.destination).blob(filename)
        blob.upload_from_string(bytes, content_type='application/octet-stream')


    def load(self, filename):
        blob = self.client.bucket(self.destination).blob(filename)
        bytes = blob.download_as_string()
        return bytes

    def delete(self, filename):
        blob = self.client.bucket(self.destination).blob(filename)
        blob.delete()
