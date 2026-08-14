from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app

client = TestClient(app)

temp_path = Path('temp_test_audio.m4a')
with temp_path.open('wb') as f:
    f.write(b'RIFF....\x00\x00\x00')

with temp_path.open('rb') as f:
    files = {'file': ('test_emergency_audio.m4a', f, 'audio/m4a')}
    data = {'language': 'en'}
    response = client.post('/api/v1/emergency-calls/audio', files=files, data=data)
    print('status', response.status_code)
    print('text', response.text)

if temp_path.exists():
    temp_path.unlink()
