"""Brand generated Flutter web scaffolding for the personal trial."""
import json
from pathlib import Path
manifest = Path('web/manifest.json')
data = json.loads(manifest.read_text())
data.update(name='WAZEN | وازن', short_name='WAZEN', description='وازن — تغذيتك اليومية',
            display='standalone', theme_color='#16665B', background_color='#F7FAF8')
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2))
index = Path('web/index.html')
s = index.read_text().replace('<title>wazen_mobile</title>', '<title>WAZEN | وازن</title>')
s = s.replace('content="wazen_mobile"', 'content="WAZEN"')
index.write_text(s)
