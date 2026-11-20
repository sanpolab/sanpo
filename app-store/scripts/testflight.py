"""TestFlight の社内テスト：グループを作って、Appの管理者（アカウント保有者など）をテスターに入れる。全ビルドが自動で配られる"""
from common import *
APP = find_app(); assert APP
gs = (call("GET", f"/v1/apps/{APP}/betaGroups?limit=50") or {}).get("data", [])
g = next((x for x in gs if x["attributes"].get("isInternalGroup")), None)
if not g:
    r = call("POST", "/v1/betaGroups", {"data": {"type": "betaGroups", "attributes": {"name": "社内テスト", "isInternalGroup": True, "hasAccessToAllBuilds": True},
             "relationships": {"app": {"data": {"type": "apps", "id": APP}}}}})
    g = r and r["data"]; print("グループを作成")
G = g["id"]
users = (call("GET", "/v1/users?limit=50") or {}).get("data", [])
for u in users:
    a = u["attributes"]; roles = a.get("roles", [])
    if not any(x in roles for x in ("ACCOUNT_HOLDER", "ADMIN", "APP_MANAGER", "DEVELOPER")): continue
    em = a.get("username") or a.get("email")
    r = call("POST", "/v1/betaTesters", {"data": {"type": "betaTesters", "attributes": {"email": em, "firstName": a.get("firstName", ""), "lastName": a.get("lastName", "")},
             "relationships": {"betaGroups": {"data": [{"type": "betaGroups", "id": G}]}}}}, ok=(201, 200, 409), quiet=True)
    print("テスター追加:", "ok" if r is not None else "既にいるかも")
bs = (call("GET", f"/v1/builds?filter[app]={APP}&sort=-uploadedDate&limit=3") or {}).get("data", [])
for b in bs: print("build", b["attributes"]["version"], b["attributes"]["processingState"])
if problems: print("\n".join(problems))

# テスターの状態を見て、招待メールを（もう一度）送る
ts = (call("GET", f"/v1/betaGroups/{G}/betaTesters?limit=50") or {}).get("data", [])
for t in ts:
    a = t["attributes"]; em = a.get("email") or ""
    masked = (em[:2] + "***@" + em.split("@")[-1]) if "@" in em else "?"
    print("tester", masked, a.get("inviteType"), a.get("state"))
    r = call("POST", "/v1/betaTesterInvitations", {"data": {"type": "betaTesterInvitations",
             "relationships": {"app": {"data": {"type": "apps", "id": APP}}, "betaTester": {"data": {"type": "betaTesters", "id": t["id"]}}}}}, ok=(200, 201, 409), quiet=False)
    print("  招待メール:", "送信" if r is not None else "送れなかった")
if not ts: print("グループにテスターがいません")
