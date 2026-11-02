"""バージョン1.0を審査に提出する（すでに提出中なら何もしない）"""
import os, time, jwt, requests
KEY_ID = os.environ["ASC_KEY_ID"]; ISSUER = os.environ["ASC_ISSUER_ID"]; P8 = os.environ["ASC_KEY_P8"]
API = "https://api.appstoreconnect.apple.com"
def tok():
    n = int(time.time()); return jwt.encode({"iss": ISSUER, "iat": n, "exp": n + 1100, "aud": "appstoreconnect-v1"}, P8, algorithm="ES256", headers={"kid": KEY_ID})
def call(m, p, b=None):
    r = requests.request(m, API + p, json=b, headers={"Authorization": "Bearer " + tok()})
    if r.status_code >= 300:
        errs = r.json().get("errors", []) if r.content else []
        print(f"! {m} {p.split('?')[0]} -> {r.status_code}")
        for e in errs:
            print("   -", e.get("code", ""), e.get("detail") or e.get("title"))
            for x in (e.get("meta") or {}).get("associatedErrors", {}).values():
                for y in x: print("      ·", y.get("detail") or y.get("title"))
        raise SystemExit(1)
    return r.json() if r.content else {}
APP = call("GET", "/v1/apps?filter[bundleId]=io.github.sanpolab.sanpo")["data"][0]["id"]
ver = next(v for v in call("GET", f"/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5")["data"])
st = ver["attributes"]["appStoreState"]; print("version state:", st)
if st in ("WAITING_FOR_REVIEW", "IN_REVIEW", "PENDING_DEVELOPER_RELEASE", "READY_FOR_SALE"):
    print("すでに提出済みです"); raise SystemExit(0)
subs = call("GET", f"/v1/reviewSubmissions?filter[app]={APP}&filter[platform]=IOS&filter[state]=READY_FOR_REVIEW,UNRESOLVED_ISSUES")["data"]
sub = subs[0] if subs else call("POST", "/v1/reviewSubmissions", {"data": {"type": "reviewSubmissions", "attributes": {"platform": "IOS"},
        "relationships": {"app": {"data": {"type": "apps", "id": APP}}}}})["data"]
items = call("GET", f"/v1/reviewSubmissions/{sub['id']}/items")["data"]
if not items:
    call("POST", "/v1/reviewSubmissionItems", {"data": {"type": "reviewSubmissionItems",
        "relationships": {"reviewSubmission": {"data": {"type": "reviewSubmissions", "id": sub["id"]}},
                          "appStoreVersion": {"data": {"type": "appStoreVersions", "id": ver["id"]}}}}})
call("PATCH", f"/v1/reviewSubmissions/{sub['id']}", {"data": {"type": "reviewSubmissions", "id": sub["id"], "attributes": {"submitted": True}}})
print("審査に提出しました")
