from pathlib import Path
import os, tempfile, subprocess, sys
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='risk-003-e2e-') as temporary:
    env={**os.environ,'APP_DB':str(Path(temporary)/'test.db'),'SEED_PATH':str(root/'data/seed.json'),
         'SEED_META_PATH':str(root/'data/seed.meta.json'),'AS_OF':'2026-10-23T18:00:00.000Z',
         'ADMIN_EMAIL':'admin@example.test','ADMIN_PASSWORD':'admin123','SEED_ON_START':'true',
         'PYTHONPATH':str(root/'backend'),'PYTHONDONTWRITEBYTECODE':'1'}
    subprocess.run([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8130'],cwd=root,env=env,check=True)
