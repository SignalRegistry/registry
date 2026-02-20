import requests
import json



def test_flows_post():
    """An initial test for the app."""
    res = requests.post(
        "https://127.0.0.1:5000/flows",
        json={"name": "trivial"},
        verify=False,
    )
    print("")
    # print("- Request headers: \n", res.request.headers)
    # print("- Request body: \n", res.request.body)
    # print("- Response headers: \n", res.headers)
    print("- Response body: \n", json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 201

def test_flows_get():
    """An initial test for the app."""
    res = requests.get("https://127.0.0.1:5000/flows", verify=False)
    print("")
    print(json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 200

def test_flows_get_last_only():
    """An initial test for the app."""
    res = requests.get("https://127.0.0.1:5000/flows?last_only=1", verify=False)
    print("")
    print(json.dumps(res.json(), indent=4, ensure_ascii=False))
    assert res.status_code == 200
