"""アプリのID（io.github.sanpolab.jan）を Apple に登録する。登録済みなら何もしない"""
from common import *
have = call("GET", f"/v1/bundleIds?filter[identifier]={BUNDLE}")
if have and any(b["attributes"]["identifier"] == BUNDLE for b in have["data"]):
    print("登録済み:", BUNDLE)
else:
    r = call("POST", "/v1/bundleIds", {"data": {"type": "bundleIds", "attributes": {"identifier": BUNDLE, "name": "JAN Keirin", "platform": "IOS"}}})
    print("登録しました:" if r else "登録できませんでした:", BUNDLE)
app = find_app()
print("App Store Connect のアプリ:", "あり" if app else "まだありません（App Store Connect で新規作成してください）")
if problems: raise SystemExit(1)
