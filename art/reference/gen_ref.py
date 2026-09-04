"""Generate character reference art via Gemini image API. Stdlib only."""
import base64, json, os, pathlib, sys, time, urllib.request

ENV = pathlib.Path.home() / ".env"
KEY = next((l.split("=", 1)[1].strip().strip('"\'')
            for l in ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
            if l.strip().startswith("GEMINI_API_KEY=")), None)
if not KEY:
    sys.exit("GEMINI_API_KEY not found in ~/.env")

OUT = pathlib.Path(__file__).parent


FALLBACK = "gemini-2.5-flash-image"


def gen(model: str, prompt: str, out_name: str, aspect: str | None = None,
        retry: bool = True, refs: list[str] | None = None) -> bool:
    # reference images go FIRST so the model treats them as the thing to match
    parts: list[dict] = []
    for r in refs or []:
        p = pathlib.Path(r)
        if not p.is_absolute():
            p = OUT / r
        parts.append({"inline_data": {
            "mime_type": "image/png",
            "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text": prompt})
    body: dict = {"contents": [{"parts": parts}],
                  "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
    if aspect:
        body["generationConfig"]["imageConfig"] = {"aspectRatio": aspect}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    # 503 = transient demand spike, not a bad request. Back off and retry the same
    # model before falling back; both models spiking at once is common.
    data = None
    for attempt in range(4):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=540))
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code in (503, 429) and attempt < 3:
                wait = 20 * (attempt + 1)
                print(f"[{out_name}] {e.code} on {model}, retry {attempt + 1}/3 in {wait}s")
                time.sleep(wait)
                continue
            print(f"[{out_name}] HTTP {e.code} on {model}: {body}")
            if retry and model != FALLBACK:
                print(f"[{out_name}] falling back to {FALLBACK}")
                return gen(FALLBACK, prompt, out_name, aspect, False, refs)
            return False
    if data is None:
        return False

    saved = False
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            dest = OUT / out_name
            dest.write_bytes(base64.b64decode(part["inlineData"]["data"]))
            print(f"saved {dest}")
            saved = True
        elif part.get("text"):
            print(f"[{out_name}] {part['text'][:200]}")
    if not saved:
        print(f"[{out_name}] no image returned — {json.dumps(data)[:400]}")
    return saved


if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    for job in spec:
        gen(job.get("model", "gemini-3-pro-image"),
            job["prompt"], job["out"], job.get("aspect"),
            refs=job.get("refs"))
