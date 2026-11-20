"""App Store Connect API の共通部分（鍵は画面に出さない）"""
import os, time, jwt, requests
KEY_ID = os.environ["ASC_KEY_ID"]; ISSUER = os.environ["ASC_ISSUER_ID"]; P8 = os.environ["ASC_KEY_P8"]
API = "https://api.appstoreconnect.apple.com"
BUNDLE = "io.github.sanpolab.jan"
problems = []
def token():
    n = int(time.time())
    return jwt.encode({"iss": ISSUER, "iat": n, "exp": n + 1100, "aud": "appstoreconnect-v1"}, P8, algorithm="ES256", headers={"kid": KEY_ID})
S = requests.Session()
def call(method, path, body=None, ok=(200, 201, 204), quiet=False):
    r = S.request(method, API + path, json=body, headers={"Authorization": "Bearer " + token()})
    if r.status_code not in ok:
        msg = f"{method} {path.split('?')[0]} -> {r.status_code}: "
        try:
            for e in r.json().get("errors", []):
                msg += (e.get("detail") or e.get("title", "")) + "; "
                for x in (e.get("meta") or {}).get("associatedErrors", {}).values():
                    for y in x: msg += (y.get("detail") or y.get("title", "")) + "; "
        except Exception: pass
        msg = msg[:900]
        if not quiet: print("  ! " + msg); problems.append(msg)
        return None
    return r.json() if r.content else {}
def find_app():
    apps = call("GET", f"/v1/apps?filter[bundleId]={BUNDLE}")
    return apps["data"][0]["id"] if apps and apps.get("data") else None
