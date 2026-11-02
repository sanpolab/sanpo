// にくきゅうレーダー：お知らせをiPhoneにプッシュ通知で送る
// 受け取るのは { id: お知らせの番号 } だけ。文面はデータベースから作るので、外から勝手な通知は送れない。
import { createClient } from "npm:@supabase/supabase-js@2.49.4";

const TEAM_ID = Deno.env.get("APNS_TEAM_ID")!;
const KEY_ID = Deno.env.get("APNS_KEY_ID")!;
const KEY_P8 = Deno.env.get("APNS_KEY_P8")!;
const TOPIC = "io.github.sanpolab.sanpo";
const APNS_HOST = "https://api.push.apple.com";

const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false },
});

// ---- Appleに送るための署名（50分ごとに作り直す） ----
let jwtCache: { token: string; at: number } | null = null;
const b64url = (buf: ArrayBuffer | Uint8Array | string) => {
  const bytes = typeof buf === "string" ? new TextEncoder().encode(buf) : new Uint8Array(buf);
  let s = ""; bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
async function apnsJwt() {
  const now = Math.floor(Date.now() / 1000);
  if (jwtCache && now - jwtCache.at < 3000) return jwtCache.token;
  const pem = KEY_P8.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const head = b64url(JSON.stringify({ alg: "ES256", kid: KEY_ID }));
  const body = b64url(JSON.stringify({ iss: TEAM_ID, iat: now }));
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, new TextEncoder().encode(`${head}.${body}`));
  const token = `${head}.${body}.${b64url(sig)}`;
  jwtCache = { token, at: now };
  return token;
}

function text(kind: string, who: string, comment?: string) {
  switch (kind) {
    case "like": return `${who} があなたの投稿に肉球を押しました`;
    case "comment": return `${who} がコメントしました${comment ? "：「" + comment.slice(0, 40) + "」" : ""}`;
    case "follow": return `${who} にフォローされました`;
    case "follow_request": return `${who} からフォローリクエストが届きました`;
    case "follow_accept": return `${who} がフォローを承認しました`;
    case "message": return `${who} からメッセージが届きました`; // 本文は通知に出さない（ロック画面で見られないように）
    default: return "";
  }
}

Deno.serve(async (req) => {
  try {
    const { id } = await req.json().catch(() => ({}));
    if (!Number.isInteger(id)) return new Response("bad request", { status: 400 });

    // まだ送っていないお知らせだけを、送信済みにしてから取り出す（2回送らない）
    const { data: n } = await sb.from("notifications")
      .update({ pushed_at: new Date().toISOString() })
      .eq("id", id).is("pushed_at", null)
      .select("id,user_id,actor_id,kind,comment_id").maybeSingle();
    if (!n) return new Response("skip");

    const [{ data: actor }, { data: tokens }, { data: cm }, { count }] = await Promise.all([
      sb.from("profiles").select("dog_name,nickname").eq("id", n.actor_id).maybeSingle(),
      sb.from("push_tokens").select("token").eq("user_id", n.user_id),
      n.comment_id ? sb.from("comments").select("body").eq("id", n.comment_id).maybeSingle() : Promise.resolve({ data: null }),
      sb.from("notifications").select("id", { count: "exact", head: true }).eq("user_id", n.user_id).eq("read", false),
    ]);
    if (!tokens?.length) return new Response("no tokens");
    const who = actor?.dog_name || actor?.nickname || "だれか";
    const body = text(n.kind, who, cm?.body);
    if (!body) return new Response("skip");

    const jwt = await apnsJwt();
    const payload = JSON.stringify({
      aps: { alert: { title: "にくきゅうレーダー", body }, sound: "default", badge: count ?? 1 },
      kind: n.kind,
    });
    await Promise.all(tokens.map(async ({ token }) => {
      const r = await fetch(`${APNS_HOST}/3/device/${token}`, {
        method: "POST",
        headers: { authorization: `bearer ${jwt}`, "apns-topic": TOPIC, "apns-push-type": "alert", "apns-priority": "10" },
        body: payload,
      });
      // もう使われていないiPhoneは登録から外す
      if (r.status === 410 || r.status === 400) {
        const e = await r.json().catch(() => ({}));
        if (r.status === 410 || e.reason === "BadDeviceToken") await sb.from("push_tokens").delete().eq("token", token);
      }
    }));
    return new Response("ok");
  } catch (e) {
    console.error(e);
    return new Response("error", { status: 500 });
  }
});
