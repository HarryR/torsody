from app import backend
x = backend.Api()
#x.prosody_create('localhost')
#x.prosody_useradd('localhost', 'harry', 'test')
#x.prosody_remove('localhost')
[x.tor_delete(y) for y in x.tor_list()]