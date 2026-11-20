"""App Store Connect に、打鐘 -JAN- のストア情報をまとめて入力する（何度動かしても同じ結果）"""
import os, hashlib, pathlib, requests
from common import *
ROOT = pathlib.Path(__file__).resolve().parents[2]
DESC = (ROOT / "app-store" / "description.txt").read_text().strip()
NOTES = (ROOT / "app-store" / "review-notes.txt").read_text().strip()
SUBTITLE = "ラインで勝負する3D競輪レース"
PROMO = "打鐘が鳴ったら勝負どころ。ラインを組んで風をよけ、まくるか差すか。1レース約1分、スマホで遊べる本格3D競輪。"
KEYWORDS = "競輪,けいりん,自転車,レース,ケイリン,打鐘,ライン,まくり,ガールズ,バンク,オンライン,対戦,スポーツ,サイクル"
KEYWORDS = KEYWORDS.replace(",ガールズ", "")
SUPPORT = "https://sanpolab.github.io/jan/support.html"
PRIVACY = "https://sanpolab.github.io/jan/privacy.html"
def step(t): print("\n== " + t)

step("アプリを探す")
APP = find_app()
if not APP: raise SystemExit("App Store Connect にアプリがありません。先に新規作成してください")
print("  app ok")
call("PATCH", f"/v1/apps/{APP}", {"data": {"type": "apps", "id": APP, "attributes": {"contentRightsDeclaration": "DOES_NOT_USE_THIRD_PARTY_CONTENT"}}})

step("アプリ情報（サブタイトル・プライバシーポリシー・カテゴリ）")
infos = call("GET", f"/v1/apps/{APP}/appInfos")["data"]
info = next((i for i in infos if i["attributes"].get("appStoreState") in ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "WAITING_FOR_REVIEW", None)), infos[0])
INFO = info["id"]
locs = call("GET", f"/v1/appInfos/{INFO}/appInfoLocalizations")["data"]
ja = next((l for l in locs if l["attributes"]["locale"] == "ja"), None)
attrs = {"subtitle": SUBTITLE, "privacyPolicyUrl": PRIVACY}
if ja: call("PATCH", f"/v1/appInfoLocalizations/{ja['id']}", {"data": {"type": "appInfoLocalizations", "id": ja["id"], "attributes": attrs}})
else: print("  ! 日本語の情報がありません（アプリ作成時の言語を確認）"); problems.append("no ja appInfoLocalization")
call("PATCH", f"/v1/appInfos/{INFO}", {"data": {"type": "appInfos", "id": INFO, "relationships": {
    "primaryCategory": {"data": {"type": "appCategories", "id": "GAMES"}},
    "primarySubcategoryOne": {"data": {"type": "appCategories", "id": "GAMES_RACING"}},
    "primarySubcategoryTwo": {"data": {"type": "appCategories", "id": "GAMES_SPORTS"}},
    "secondaryCategory": {"data": {"type": "appCategories", "id": "SPORTS"}}}}})

step("年齢制限の質問")
ard = call("GET", f"/v1/appInfos/{INFO}/ageRatingDeclaration")
if ard:
    AR = ard["data"]["id"]; cur = ard["data"]["attributes"]
    # ガチャ（ゲーム内コインのみ）＝ルートボックスあり。観戦の1着予想（無料チップ）＝ギャンブルの模擬：まれ/軽度
    BOOL = {"messagingAndChat": False, "userGeneratedContent": False, "socialMedia": False,
            "socialMediaAgeRestricted": False, "advertising": False, "gambling": False, "lootBox": True,
            "parentalControls": False, "ageAssurance": False, "unrestrictedWebAccess": False,
            "healthOrWellnessTopics": False}
    LEVEL = {"alcoholTobaccoOrDrugUseOrReferences": "NONE", "contests": "NONE", "gamblingSimulated": "INFREQUENT_OR_MILD",
             "horrorOrFearThemes": "NONE", "matureOrSuggestiveThemes": "NONE", "medicalOrTreatmentInformation": "NONE",
             "profanityOrCrudeHumor": "NONE", "sexualContentGraphicAndNudity": "NONE", "sexualContentOrNudity": "NONE",
             "violenceCartoonOrFantasy": "NONE", "violenceRealistic": "NONE",
             "violenceRealisticProlongedGraphicOrSadistic": "NONE", "gunsOrOtherWeapons": "NONE"}
    want = {k: v for k, v in BOOL.items() if k in cur}
    want.update({k: v for k, v in LEVEL.items() if k in cur})
    call("PATCH", f"/v1/ageRatingDeclarations/{AR}", {"data": {"type": "ageRatingDeclarations", "id": AR, "attributes": want}})
    # 新しく増えた質問（出会い・位置情報の共有）は「なし」。はい/いいえ型か頻度型かわからないので両方試す
    for k in ("datingAndRelationships", "sharedLocation"):
        if k in cur:
            if not call("PATCH", f"/v1/ageRatingDeclarations/{AR}", {"data": {"type": "ageRatingDeclarations", "id": AR, "attributes": {k: False}}}, quiet=True):
                call("PATCH", f"/v1/ageRatingDeclarations/{AR}", {"data": {"type": "ageRatingDeclarations", "id": AR, "attributes": {k: "NONE"}}})
            want[k] = True
    unknown = [k for k in cur if k not in want and k not in ("kidsAgeBand", "ageRatingOverride", "koreaAgeRatingOverride", "ageRatingOverrideV2", "koreaAgeRatingOverrideV2", "developerAgeRatingInfoUrl")]
    if unknown: print("  未回答の質問:", ", ".join(unknown))

step("バージョン1.0の説明文")
vers = call("GET", f"/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5")["data"]
ver = next(v for v in vers if v["attributes"]["appStoreState"] in ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED"))
VER = ver["id"]
call("PATCH", f"/v1/appStoreVersions/{VER}", {"data": {"type": "appStoreVersions", "id": VER, "attributes": {"copyright": "2026 EIJI ISHIBASHI", "releaseType": "MANUAL"}}})
vl = call("GET", f"/v1/appStoreVersions/{VER}/appStoreVersionLocalizations")["data"]
jav = next((l for l in vl if l["attributes"]["locale"] == "ja"), None)
va = {"description": DESC, "keywords": KEYWORDS, "promotionalText": PROMO, "supportUrl": SUPPORT, "marketingUrl": "https://sanpolab.github.io/jan/"}
if jav: call("PATCH", f"/v1/appStoreVersionLocalizations/{jav['id']}", {"data": {"type": "appStoreVersionLocalizations", "id": jav["id"], "attributes": va}})
else: jav = call("POST", "/v1/appStoreVersionLocalizations", {"data": {"type": "appStoreVersionLocalizations", "attributes": dict(locale="ja", **va), "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": VER}}}}})["data"]

step("いちばん新しいビルドを選ぶ")
builds = (call("GET", f"/v1/builds?filter[app]={APP}&sort=-uploadedDate&limit=5") or {}).get("data", [])
good = [b for b in builds if b["attributes"]["processingState"] == "VALID"]
if good:
    B = good[0]
    call("PATCH", f"/v1/builds/{B['id']}", {"data": {"type": "builds", "id": B["id"], "attributes": {"usesNonExemptEncryption": False}}}, quiet=True)
    call("PATCH", f"/v1/appStoreVersions/{VER}/relationships/build", {"data": {"type": "builds", "id": B["id"]}})
    print("  build", B["attributes"]["version"])
else: print("  まだ処理済みのビルドがありません")

step("審査への連絡事項")
rd = call("GET", f"/v1/appStoreVersions/{VER}/appStoreReviewDetail", ok=(200,), quiet=True)
ra = {"contactFirstName": "EIJI", "contactLastName": "ISHIBASHI", "contactEmail": os.environ.get("REVIEW_CONTACT_EMAIL", ""),
      "demoAccountRequired": False, "notes": NOTES}
phone = os.environ.get("REVIEW_CONTACT_PHONE", "")
if not phone:   # にくきゅうレーダーの審査用連絡先と同じ電話番号を使う（画面には出さない）
    other = call("GET", "/v1/apps?filter[bundleId]=io.github.sanpolab.sanpo", quiet=True)
    if other and other.get("data"):
        for v in (call("GET", f"/v1/apps/{other['data'][0]['id']}/appStoreVersions?limit=5", quiet=True) or {}).get("data", []):
            d = call("GET", f"/v1/appStoreVersions/{v['id']}/appStoreReviewDetail", ok=(200,), quiet=True)
            if d and d.get("data") and d["data"]["attributes"].get("contactPhone"):
                phone = d["data"]["attributes"]["contactPhone"]
                if not ra.get("contactEmail"): ra["contactEmail"] = d["data"]["attributes"].get("contactEmail") or ""
                break
if phone: ra["contactPhone"] = phone
else: print("  ! 審査用の電話番号が見つかりません")
if not ra["contactEmail"]: del ra["contactEmail"]
if rd and rd.get("data"):
    call("PATCH", f"/v1/appStoreReviewDetails/{rd['data']['id']}", {"data": {"type": "appStoreReviewDetails", "id": rd["data"]["id"], "attributes": ra}})
else:
    call("POST", "/v1/appStoreReviewDetails", {"data": {"type": "appStoreReviewDetails", "attributes": ra, "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": VER}}}}})

step("スクリーンショット（横向き 2796x1290）")
shots = sorted((ROOT / "app-store" / "screenshots").glob("jan*.png"))
sets = call("GET", f"/v1/appStoreVersionLocalizations/{jav['id']}/appScreenshotSets")["data"]
ss = next((s for s in sets if s["attributes"]["screenshotDisplayType"] == "APP_IPHONE_67"), None)
if not ss:
    ss = call("POST", "/v1/appScreenshotSets", {"data": {"type": "appScreenshotSets", "attributes": {"screenshotDisplayType": "APP_IPHONE_67"},
          "relationships": {"appStoreVersionLocalization": {"data": {"type": "appStoreVersionLocalizations", "id": jav["id"]}}}}})
    ss = ss and ss["data"]
if ss:
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
if sched and sched.get("included"): print("  already set")
else:
    pts = call("GET", f"/v1/apps/{APP}/appPricePoints?filter[territory]=USA&limit=200")
    free = next((p for p in (pts or {}).get("data", []) if float(p["attributes"]["customerPrice"]) == 0), None)
    if free:
        call("POST", "/v1/appPriceSchedules", {"data": {"type": "appPriceSchedules", "relationships": {
            "app": {"data": {"type": "apps", "id": APP}}, "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
            "manualPrices": {"data": [{"type": "appPrices", "id": "${price0}"}]}}},
            "included": [{"type": "appPrices", "id": "${price0}", "attributes": {"startDate": None},
                          "relationships": {"appPricePoint": {"data": {"type": "appPricePoints", "id": free["id"]}}}}]})
        print("  free")

step("配信する国（日本）")
av = call("GET", f"/v1/apps/{APP}/appAvailabilityV2", ok=(200,), quiet=True)
if av and av.get("data"): print("  already set")
else:
    terrs = [t["id"] for t in call("GET", "/v1/territories?limit=200")["data"]]
    r = call("POST", "/v2/appAvailabilities", {"data": {"type": "appAvailabilities", "attributes": {"availableInNewTerritories": False},
        "relationships": {"app": {"data": {"type": "apps", "id": APP}},
                          "territoryAvailabilities": {"data": [{"type": "territoryAvailabilities", "id": "${t%s}" % t} for t in terrs]}}},
        "included": [{"type": "territoryAvailabilities", "id": "${t%s}" % t, "attributes": {"available": t == "JPN"},
                      "relationships": {"territory": {"data": {"type": "territories", "id": t}}}} for t in terrs]})
    if r: print("  Japan")

print("\n== 結果")
if problems: print("うまくいかなかった項目:"); [print(" - " + p) for p in problems]
else: print("すべて入力できました")
