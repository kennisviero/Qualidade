import os
import tempfile
import uuid

os.environ["QUALIDADE_DB"] = os.path.join(
    tempfile.gettempdir(), f"qualidade_test_{uuid.uuid4().hex}.db"
)
os.environ["QUALIDADE_DOCS"] = os.path.join(
    tempfile.gettempdir(), f"qualidade_docs_{uuid.uuid4().hex}"
)
