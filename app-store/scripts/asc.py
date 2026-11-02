"""App Store Connect に、ストアの情報をまとめて入力する（何度動かしても同じ結果になる）。
鍵やパスワードは画面に出さない。"""
import os, sys, time, json, hashlib, secrets, string, pathlib
import jwt, requests

KEY_ID = os.environ["ASC_KEY_ID"]; ISSUER = os.environ["ASC_ISSUER_ID"]; P8 = os.environ["ASC_KEY_P8"]
BUNDLE = "io.github.sanpolab.sanpo"
ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "https://api.appstoreconnect.apple.com"
problems = []

def token():
    now = int(time.time())
    return jwt.encode({"iss": ISSUER, "iat": now, "exp": now + 1100, "aud": "appstoreconnect-v1"}, P8, algorithm="ES256", headers={"kid": KEY_ID})
S = requests.Session()
def call(method, path, body=None, ok=(200, 201, 204), quiet=False):
    r = S.request(method, API + path, json=body, headers={"Authorization": "Bearer " + token()})
    if r.status_code not in ok:
        msg = f"{method} {path.split('?')[0]} -> {r.status_code}: " + "; ".join(e.get("detail") or e.get("title", "") for e in r.json().get("errors", [])) if r.content else ""
        if not quiet: print("  ! " + msg); problems.append(msg)
        return None
    return r.json() if r.content else {}

def step(t): print("\n== " + t)

# ---------- 文章 ----------
meta = (ROOT / "app-store" / "metadata.md").read_text()
DESC = (ROOT / "app-store" / "description.txt").read_text().strip()
SUBTITLE = "肉球やけど・熱中症から守るおさんぽ判定"
PROMO = "夏はアスファルトのやけど、冬は凍結。今日のおさんぽ、いつ行けば安心？天気と地面の温度から、犬と猫それぞれにぴったりの時間をお知らせします。"
KEYWORDS = "犬,猫,散歩,ペット,肉球,熱中症,アスファルト,路面温度,ドッグラン,天気,迷子,記録,いぬ,ねこ,わんこ,お散歩"
SUPPORT = "https://sanpolab.github.io/sanpo/#support"
PRIVACY = "https://sanpolab.github.io/sanpo/#privacy"

step("アプリを探す")
apps = call("GET", f"/v1/apps?filter[bundleId]={BUNDLE}")
app = apps["data"][0]; APP = app["id"]; print("  app ok")

step("著作権の確認（地図・天気の外部データを使用）")
call("PATCH", f"/v1/apps/{APP}", {"data": {"type": "apps", "id": APP, "attributes": {"contentRightsDeclaration": "USES_THIRD_PARTY_CONTENT"}}})

step("アプリ情報（サブタイトル・プライバシーポリシー・カテゴリ）")
infos = call("GET", f"/v1/apps/{APP}/appInfos")["data"]
info = next((i for i in infos if i["attributes"].get("appStoreState") in ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "WAITING_FOR_REVIEW", None)), infos[0])
INFO = info["id"]
locs = call("GET", f"/v1/appInfos/{INFO}/appInfoLocalizations")["data"]
ja = next((l for l in locs if l["attributes"]["locale"] == "ja"), None)
attrs = {"subtitle": SUBTITLE, "privacyPolicyUrl": PRIVACY}
if ja: call("PATCH", f"/v1/appInfoLocalizations/{ja['id']}", {"data": {"type": "appInfoLocalizations", "id": ja["id"], "attributes": attrs}})
else: call("POST", "/v1/appInfoLocalizations", {"data": {"type": "appInfoLocalizations", "attributes": dict(locale="ja", name="にくきゅうレーダー", **attrs), "relationships": {"appInfo": {"data": {"type": "appInfos", "id": INFO}}}}})
call("PATCH", f"/v1/appInfos/{INFO}", {"data": {"type": "appInfos", "id": INFO, "relationships": {
    "primaryCategory": {"data": {"type": "appCategories", "id": "LIFESTYLE"}},
    "secondaryCategory": {"data": {"type": "appCategories", "id": "WEATHER"}}}}})

step("年齢制限の質問")
ard = call("GET", f"/v1/appInfos/{INFO}/ageRatingDeclaration")
if ard:
    AR = ard["data"]["id"]; cur = ard["data"]["attributes"]
    # はい／いいえで答える質問（このアプリ：交流・投稿・メッセージあり、それ以外はなし）
    BOOL = {"messagingAndChat": True, "userGeneratedContent": True, "socialMedia": True,
            "socialMediaAgeRestricted": False, "advertising": False, "gambling": False, "lootBox": False,
            "parentalControls": False, "ageAssurance": False, "unrestrictedWebAccess": False,
            "healthOrWellnessTopics": False}
    # 頻度で答える質問は、すべて「なし」
    LEVEL = ["alcoholTobaccoOrDrugUseOrReferences", "contests", "gamblingSimulated", "horrorOrFearThemes",
             "matureOrSuggestiveThemes", "medicalOrTreatmentInformation", "profanityOrCrudeHumor",
             "sexualContentGraphicAndNudity", "sexualContentOrNudity", "violenceCartoonOrFantasy",
             "violenceRealistic", "violenceRealisticProlongedGraphicOrSadistic", "gunsOrOtherWeapons"]
    want = {k: v for k, v in BOOL.items() if k in cur}
    want.update({k: "NONE" for k in LEVEL if k in cur})
    call("PATCH", f"/v1/ageRatingDeclarations/{AR}", {"data": {"type": "ageRatingDeclarations", "id": AR, "attributes": want}})
    unknown = [k for k in cur if k not in want and k not in ("kidsAgeBand", "ageRatingOverride", "koreaAgeRatingOverride", "ageRatingOverrideV2", "koreaAgeRatingOverrideV2", "developerAgeRatingInfoUrl")]
    if unknown: print("  未回答の質問:", ", ".join(unknown))

step("バージョン1.0の説明文")
vers = call("GET", f"/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5")["data"]
ver = next(v for v in vers if v["attributes"]["appStoreState"] in ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED"))
VER = ver["id"]
call("PATCH", f"/v1/appStoreVersions/{VER}", {"data": {"type": "appStoreVersions", "id": VER, "attributes": {
    "copyright": "2026 EIJI ISHIBASHI", "releaseType": "MANUAL"}}})
vl = call("GET", f"/v1/appStoreVersions/{VER}/appStoreVersionLocalizations")["data"]
jav = next((l for l in vl if l["attributes"]["locale"] == "ja"), None)
va = {"description": DESC, "keywords": KEYWORDS, "promotionalText": PROMO, "supportUrl": SUPPORT}
if jav: call("PATCH", f"/v1/appStoreVersionLocalizations/{jav['id']}", {"data": {"type": "appStoreVersionLocalizations", "id": jav["id"], "attributes": va}})
else:
    jav = call("POST", "/v1/appStoreVersionLocalizations", {"data": {"type": "appStoreVersionLocalizations", "attributes": dict(locale="ja", **va), "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": VER}}}}})["data"]

step("いちばん新しいビルドを選ぶ")
builds = call("GET", f"/v1/builds?filter[app]={APP}&sort=-uploadedDate&limit=5")["data"]
good = [b for b in builds if b["attributes"]["processingState"] == "VALID"]
if good:
    B = good[0]; call("PATCH", f"/v1/appStoreVersions/{VER}/relationships/build", {"data": {"type": "builds", "id": B["id"]}})
    print("  build", B["attributes"]["version"])

step("審査用アカウント")
REVIEW_PASS = os.environ.get("REVIEW_PASSWORD", "")
rd = call("GET", f"/v1/appStoreVersions/{VER}/appStoreReviewDetail", ok=(200,), quiet=True)
notes = ("にくきゅうレーダーは、天気と地面の温度から、犬や猫の散歩に安全な時間を判定するアプリです。\n"
         "判定・地図は位置情報を許可すると現在地で動きます（許可しなくても地名で検索できます）。\n"
         "投稿・コメント・メッセージなどの交流機能を試すには、マイページの「パスワードでログイン」から下記のデモアカウントでログインしてください。\n"
         "不適切な投稿やユーザーは、各投稿の「…」やユーザー画面から通報・ブロックでき、運営者が24時間以内に確認・削除します。\n"
         "位置情報のバックグラウンド利用は、利用者が「おさんぽスタート」を押してから「おわった」を押すまでの間だけ、歩いた道のりの記録に使います。")
ra = {"contactFirstName": "EIJI", "contactLastName": "ISHIBASHI", "contactEmail": "nakanakadoukana@gmail.com",
      "demoAccountRequired": True, "demoAccountName": "nakanakadoukana+review@gmail.com", "notes": notes}
if REVIEW_PASS: ra["demoAccountPassword"] = REVIEW_PASS
if rd and rd.get("data"):
    call("PATCH", f"/v1/appStoreReviewDetails/{rd['data']['id']}", {"data": {"type": "appStoreReviewDetails", "id": rd["data"]["id"], "attributes": ra}})
else:
    call("POST", "/v1/appStoreReviewDetails", {"data": {"type": "appStoreReviewDetails", "attributes": ra, "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": VER}}}}})

step("スクリーンショット")
shots = sorted((ROOT / "app-store" / "screenshots").glob("storeR*.png"))
sets = call("GET", f"/v1/appStoreVersionLocalizations/{jav['id']}/appScreenshotSets")["data"]
for dtype in ("APP_IPHONE_67",):
    ss = next((s for s in sets if s["attributes"]["screenshotDisplayType"] == dtype), None)
    if not ss:
        ss = call("POST", "/v1/appScreenshotSets", {"data": {"type": "appScreenshotSets", "attributes": {"screenshotDisplayType": dtype},
              "relationships": {"appStoreVersionLocalization": {"data": {"type": "appStoreVersionLocalizations", "id": jav["id"]}}}}})
        ss = ss and ss["data"]
    if not ss: continue
    have = call("GET", f"/v1/appScreenshotSets/{ss['id']}/appScreenshots")["data"]
    names = {h["attributes"]["fileName"] for h in have if (h["attributes"].get("assetDeliveryState") or {}).get("state") != "FAILED"}
    for h in have:
        if (h["attributes"].get("assetDeliveryState") or {}).get("state") == "FAILED": call("DELETE", f"/v1/appScreenshots/{h['id']}")
    for f in shots:
        if f.name in names: print("  have", f.name); continue
        data = f.read_bytes()
        r = call("POST", "/v1/appScreenshots", {"data": {"type": "appScreenshots", "attributes": {"fileName": f.name, "fileSize": len(data)},
                 "relationships": {"appScreenshotSet": {"data": {"type": "appScreenshotSets", "id": ss["id"]}}}}})
        if not r: continue
        sid = r["data"]["id"]
        for op in r["data"]["attributes"]["uploadOperations"]:
            part = data[op["offset"]: op["offset"] + op["length"]]
            requests.request(op["method"], op["url"], data=part, headers={h["name"]: h["value"] for h in op["requestHeaders"]}).raise_for_status()
        call("PATCH", f"/v1/appScreenshots/{sid}", {"data": {"type": "appScreenshots", "id": sid, "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(data).hexdigest()}}})
        print("  uploaded", f.name)

step("価格（無料）")
sched = call("GET", f"/v1/apps/{APP}/appPriceSchedule?include=manualPrices", ok=(200,), quiet=True)
has_price = bool(sched and sched.get("included"))
if has_price: print("  already set")
else:
    pts = call("GET", f"/v1/apps/{APP}/appPricePoints?filter[territory]=USA&limit=200")
    free = next((p for p in (pts or {}).get("data", []) if float(p["attributes"]["customerPrice"]) == 0), None)
    if free:
        call("POST", "/v1/appPriceSchedules", {"data": {"type": "appPriceSchedules", "relationships": {
            "app": {"data": {"type": "apps", "id": APP}},
            "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
            "manualPrices": {"data": [{"type": "appPrices", "id": "${price0}"}]}}},
            "included": [{"type": "appPrices", "id": "${price0}", "attributes": {"startDate": None},
                          "relationships": {"appPricePoint": {"data": {"type": "appPricePoints", "id": free["id"]}}}}]})
        print("  free")

print("\n== 結果")
if problems:
    print("うまくいかなかった項目:"); [print(" - " + p) for p in problems]
else:
    print("すべて入力できました")
