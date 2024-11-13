import sounddevice as sd

def query():
    device = sd.query_devices()
    print(device)

query()