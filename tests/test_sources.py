import requests
import json


def test_sources_get():
    """An initial test for the app."""
    res = requests.get("https://127.0.0.1:5000/sources", verify=False)
    print("")
    print(json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 200


def test_sources_post():
    """An initial test for the app."""
    res = requests.post(
        "https://127.0.0.1:5000/sources",
        json={"type": "pulse", "name": "test"},
        verify=False,
    )
    print("")
    # print("- Request headers: \n", res.request.headers)
    # print("- Request body: \n", res.request.body)
    # print("- Response headers: \n", res.headers)
    print("- Response body: \n", json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 201
