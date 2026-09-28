"""Print the article body of a saved news snapshot (text after the byline marker)."""
import re, sys
f = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 900
t = open(f"sources/news/{f}.html", encoding="utf-8", errors="replace").read()
t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"&nbsp;|&#160;", " ", t); t = re.sub(r"\s+", " ", t)
for key in ["선호 출처로 추가", "기사 읽어주기", "본문 글씨", "입력"]:
    i = t.find(key)
    if i >= 0:
        break
m = re.search(r"입력 \d{4}[.-]\d{2}[.-]\d{2}[^ ]* ?[0-9:]*", t)
print(f, "|", m.group(0) if m else "", "|", t[i:i + n])
