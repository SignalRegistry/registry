import requests
import json


def test_source_delete():
    """An initial test for the app."""
    res = requests.delete("https://127.0.0.1:5000/source/64afd3", verify=False)
    print("")
    print(json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 200

def test_source_get():
    """An initial test for the app."""
    res = requests.get("https://127.0.0.1:5000/source/d03cb3", verify=False)
    print("")
    print(json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 200


