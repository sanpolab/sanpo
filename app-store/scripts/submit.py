"""バージョン1.0を審査に提出する（すでに提出中なら何もしない）"""
import os, time
from common import *
APP = find_app(); assert APP, "アプリがありません"
ver = call("GET", f"/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5")["data"][0]
st = ver["attributes"]["appStoreState"]; print("version state:", st)
if os.environ.get("STATUS_ONLY") == "1": raise SystemExit(0)
if st in ("WAITING_FOR_REVIEW", "IN_REVIEW", "PENDING_DEVELOPER_RELEASE", "READY_FOR_SALE"):
    print("すでに提出済みです"); raise SystemExit(0)
for old in (call("GET", f"/v1/reviewSubmissions?filter[app]={APP}&filter[platform]=IOS&filter[state]=UNRESOLVED_ISSUES") or {}).get("data", []):
    call("PATCH", f"/v1/reviewSubmissions/{old['id']}", {"data": {"type": "reviewSubmissions", "id": old["id"], "attributes": {"canceled": True}}}); time.sleep(5)
subs = (call("GET", f"/v1/reviewSubmissions?filter[app]={APP}&filter[platform]=IOS&filter[state]=READY_FOR_REVIEW") or {}).get("data", [])
sub = subs[0] if subs else call("POST", "/v1/reviewSubmissions", {"data": {"type": "reviewSubmissions", "attributes": {"platform": "IOS"},
    "relationships": {"app": {"data": {"type": "apps", "id": APP}}}}})["data"]
if not call("GET", f"/v1/reviewSubmissions/{sub['id']}/items")["data"]:
    call("POST", "/v1/reviewSubmissionItems", {"data": {"type": "reviewSubmissionItems", "relationships": {
        "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": sub["id"]}},
        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": ver["id"]}}}}})
r = call("PATCH", f"/v1/reviewSubmissions/{sub['id']}", {"data": {"type": "reviewSubmissions", "id": sub["id"], "attributes": {"submitted": True}}})
print("審査に提出しました" if r else "提出できませんでした（上の理由を確認）")
if problems: raise SystemExit(1)
