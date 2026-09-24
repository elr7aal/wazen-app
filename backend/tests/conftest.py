
import os, tempfile
DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
DB.close()
os.environ['DATABASE_URL'] = f"sqlite:///{DB.name}"
os.environ['WAZEN_SECRET'] = 'test-secret'
