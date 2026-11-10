import os

# Settings need a secret; set it before any `src` module is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-0123456789")
