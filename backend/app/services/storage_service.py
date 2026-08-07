"""File storage abstraction. Local filesystem for dev; the only file that
needs to change to move to Azure Blob Storage later is this one — callers
only ever deal with a `relative_path` string, never a local path directly."""

import os
import uuid

from flask import current_app


def _root():
    return current_app.config["UPLOAD_ROOT"]


def save_file(enquiry_id, file_storage):
    """Save an uploaded werkzeug FileStorage under the enquiry's folder.
    Returns the relative path to store on the JobDocument row."""
    ext = os.path.splitext(file_storage.filename or "")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    relative_path = os.path.join("enquiries", str(enquiry_id), filename)
    absolute_path = os.path.join(_root(), relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    file_storage.save(absolute_path)
    return relative_path


def save_bytes(enquiry_id, filename, data: bytes):
    """Save raw bytes (e.g. a generated PDF) under the enquiry's folder."""
    relative_path = os.path.join("enquiries", str(enquiry_id), filename)
    absolute_path = os.path.join(_root(), relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    with open(absolute_path, "wb") as f:
        f.write(data)
    return relative_path


def absolute_path_for(relative_path):
    return os.path.join(_root(), relative_path)
