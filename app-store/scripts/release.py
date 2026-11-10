"""承認済み（リリース待ち）のバージョンを App Store に公開する"""
import os, time, jwt, requests
KEY_ID = os.environ["ASC_KEY_ID"]; ISSUER = os.environ["ASC_ISSUER_ID"]; P8 = os.environ["ASC_KEY_P8"]
API = "https://api.appstoreconnect.apple.com"
def tok():
    n = int(time.time()); return jwt.encode({"iss": ISSUER, "iat": n, "exp": n + 1100, "aud": "appstoreconnect-v1"}, P8, algorithm="ES256", headers={"kid": KEY_ID})
def call(m, p, b=None):
    r = requests.request(m, API + p, json=b, headers={"Authorization": "Bearer " + tok()})
    if r.status_code >= 300:
        print(f"! {m} {p} -> {r.status_code}", [e.get("detail") for e in r.json().get("errors", [])]); raise SystemExit(1)
    return r.json() if r.content else {}
APP = call("GET", "/v1/apps?filter[bundleId]=io.github.sanpolab.sanpo")["data"][0]["id"]
ver = call("GET", f"/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5")["data"][0]
st = ver["attributes"]["appStoreState"]; print("before:", st)
if st != "PENDING_DEVELOPER_RELEASE":
    print("リリース待ちではないので、何もしません"); raise SystemExit(0)
call("POST", "/v1/appStoreVersionReleaseRequests", {"data": {"type": "appStoreVersionReleaseRequests",
    "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": ver["id"]}}}}})
time.sleep(10)
print("after:", call("GET", f"/v1/appStoreVersions/{ver['id']}")["data"]["attributes"]["appStoreState"])
