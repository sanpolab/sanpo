"""アプリ内課金の商品（コイン8種＋シーズンパス）を App Store Connect に登録する。何度動かしても同じ結果"""
import hashlib, pathlib, requests
from common import *
ROOT = pathlib.Path(__file__).resolve().parents[2]
SHOP = [(100, 160), (300, 480), (510, 800), (980, 1500), (1580, 2400), (2500, 3800), (3400, 5000), (7000, 10000)]
ITEMS = [dict(pid=f"io.github.sanpolab.jan.coin{c}", ref=f"Coin {c}", ja=f"コイン {c:,}枚", desc=f"ガチャ{c//100}回分のコイン（有効期限180日）", yen=y) for c, y in SHOP]
ITEMS.append(dict(pid="io.github.sanpolab.jan.pass", ref="Season Pass (this month)", ja="シーズンパス（今月分）", desc="今月のシーズンパスのプレミアム報酬と限定フレーム", yen=980))
NOTE = ("Consumable. Coins are spent on the in-game gacha (odds are shown in the gacha screen). "
        "The season pass unlocks this month's premium reward row; it does not renew automatically.")
SHOT = ROOT / "app-store" / "iap-review.png"
def step(t): print("\n== " + t)
APP = find_app(); assert APP, "アプリがありません"
have = {}
r = call("GET", f"/v1/apps/{APP}/inAppPurchasesV2?limit=50")
for x in (r or {}).get("data", []): have[x["attributes"]["productId"]] = x
for it in ITEMS:
    step(it["ja"])
    x = have.get(it["pid"])
    if not x:
        r = call("POST", "/v2/inAppPurchases", {"data": {"type": "inAppPurchases", "attributes": {
            "name": it["ref"], "productId": it["pid"], "inAppPurchaseType": "CONSUMABLE", "reviewNote": NOTE, "familySharable": False},
            "relationships": {"app": {"data": {"type": "apps", "id": APP}}}}})
        if not r: continue
        x = r["data"]; print("  作成")
    IID = x["id"]
    # 日本語の表示名
    locs = (call("GET", f"/v2/inAppPurchases/{IID}/inAppPurchaseLocalizations") or {}).get("data", [])
    ja = next((l for l in locs if l["attributes"]["locale"] == "ja"), None)
    la = {"name": it["ja"], "description": it["desc"]}
    if ja: call("PATCH", f"/v1/inAppPurchaseLocalizations/{ja['id']}", {"data": {"type": "inAppPurchaseLocalizations", "id": ja["id"], "attributes": la}})
    else: call("POST", "/v1/inAppPurchaseLocalizations", {"data": {"type": "inAppPurchaseLocalizations", "attributes": dict(locale="ja", **la),
              "relationships": {"inAppPurchaseV2": {"data": {"type": "inAppPurchases", "id": IID}}}}})
    # 価格（日本円で決める）
    sched = call("GET", f"/v2/inAppPurchases/{IID}/iapPriceSchedule?include=manualPrices", ok=(200,), quiet=True)
    if sched and sched.get("included"): print("  価格 設定済み")
    else:
        pts, url, pp = [], f"/v2/inAppPurchases/{IID}/pricePoints?filter[territory]=JPN&limit=200", None
        while url:
            r = call("GET", url); pts += r["data"]; nxt = r.get("links", {}).get("next"); url = nxt.replace(API, "") if nxt else None
            pp = next((p for p in pts if float(p["attributes"]["customerPrice"]) == it["yen"]), None)
            if pp: break
        if not pp: print("  ! この値段がありません", it["yen"]); problems.append(f"price {it['yen']}"); continue
        r = call("POST", "/v1/inAppPurchasePriceSchedules", {"data": {"type": "inAppPurchasePriceSchedules", "relationships": {
            "inAppPurchase": {"data": {"type": "inAppPurchases", "id": IID}},
            "baseTerritory": {"data": {"type": "territories", "id": "JPN"}},
            "manualPrices": {"data": [{"type": "inAppPurchasePrices", "id": "${p0}"}]}}},
            "included": [{"type": "inAppPurchasePrices", "id": "${p0}", "attributes": {"startDate": None},
                          "relationships": {"inAppPurchasePricePoint": {"data": {"type": "inAppPurchasePricePoints", "id": pp["id"]}}}}]})
        if r: print("  価格", it["yen"])
    # 配信国（日本）
    av = call("GET", f"/v2/inAppPurchases/{IID}/inAppPurchaseAvailability", ok=(200,), quiet=True)
    if av and av.get("data"): print("  配信国 設定済み")
    else:
        r = call("POST", "/v1/inAppPurchaseAvailabilities", {"data": {"type": "inAppPurchaseAvailabilities", "attributes": {"availableInNewTerritories": False},
            "relationships": {"inAppPurchase": {"data": {"type": "inAppPurchases", "id": IID}},
                              "availableTerritories": {"data": [{"type": "territories", "id": "JPN"}]}}}})
        if r: print("  配信国 日本")
    # 審査用スクショ
    cur = call("GET", f"/v2/inAppPurchases/{IID}/appStoreReviewScreenshot", ok=(200,), quiet=True)
    if cur and cur.get("data"): print("  審査用スクショ あり")
    elif SHOT.exists():
        data = SHOT.read_bytes()
        r = call("POST", "/v1/inAppPurchaseAppStoreReviewScreenshots", {"data": {"type": "inAppPurchaseAppStoreReviewScreenshots",
                 "attributes": {"fileName": SHOT.name, "fileSize": len(data)}, "relationships": {"inAppPurchaseV2": {"data": {"type": "inAppPurchases", "id": IID}}}}})
        if r:
            sid = r["data"]["id"]
            for op in r["data"]["attributes"]["uploadOperations"]:
                requests.request(op["method"], op["url"], data=data[op["offset"]: op["offset"] + op["length"]], headers={h["name"]: h["value"] for h in op["requestHeaders"]}).raise_for_status()
            call("PATCH", f"/v1/inAppPurchaseAppStoreReviewScreenshots/{sid}", {"data": {"type": "inAppPurchaseAppStoreReviewScreenshots", "id": sid,
                 "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(data).hexdigest()}}})
            print("  審査用スクショ アップロード")
step("状態")
r = call("GET", f"/v1/apps/{APP}/inAppPurchasesV2?limit=50")
for x in (r or {}).get("data", []): print(" ", x["attributes"]["productId"], x["attributes"].get("state"))
if problems: print("\nうまくいかなかった項目:"); [print(" - " + p) for p in problems]; raise SystemExit(1)
