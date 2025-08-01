import json

def load_prevBRD_version():
    with open("logs/brd_log.json",'r') as f:
        data=json.load(f)
    return data[-1]['brd_text']
