# -*- coding: utf-8 -*-
"""
sab_jaancho.py — नामकरण और मंडल भंडार, दोनों की पूरी जाँच.

चलाओ:  python3 tools/sab_jaancho.py

Rust की ज़रूरत नहीं. नक़ली workspace बनाकर उसी पर सब कुछ जाँचा जाता है.
"""

import os
import shutil
import sys
import tempfile

YAHAN = os.path.dirname(os.path.abspath(__file__))
JAD = os.path.dirname(YAHAN)
sys.path.insert(0, YAHAN)
sys.path.insert(0, os.path.join(JAD, "mandala"))

import nakli_workspace                                       # noqa: E402
import naamkaran                                             # noqa: E402
from mandala_bhandar import (BINDU, VALAYA_1, VALAYA_2, VALAYA_3,
                             MandalaBhandar)                 # noqa: E402

paas = 0
fail = 0


def j(naam, shart):
    global paas, fail
    if shart:
        print("  [ पास ]", naam)
        paas += 1
    else:
        print("  [ फेल ]", naam, "   <<<")
        fail += 1


# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  १. नामकरण — हर शक्ल अलग-अलग")
print("=" * 64)

nap = naamkaran


def b(t):
    """सिर्फ़ बदला हुआ text लौटाता है."""
    return nap.badlo_text(t)[0]


# जाँचें अब किसी जमे हुए नाम की उम्मीद नहीं करतीं.
#
# पहले यहाँ हर जगह 'sutra' लिखा था. फिर नाम बदलना पड़ा और सारी 62 जाँचें
# एक साथ फेल हो गईं — हालाँकि औज़ार बिल्कुल ठीक चल रहा था.
#
# सबक़ वही जो औज़ार में था: जो चीज़ बदल सकती है उसे जाँच में भी मत जमाओ.
# अब नाम औज़ार से ही पूछा जाता है.
N = nap.NAYA_NAAM.lower()
NB = nap.NAYA_NAAM.upper()
NC = nap.NAYA_NAAM.capitalize()
EXT = nap.NAYA_EXT
EXTC = nap.NAYA_EXT_CHHOTA
BIN = nap.NAYA_BINARY


j("compiler का binary",       b("klionsc build") == BIN + " build")
j("crate का नाम (dash)",      b("klions-lexer") == N + "-lexer")
j("library का नाम (underscore)",
  b("use klions_ir::Mir;") == "use %s_ir::Mir;" % N)
j("environment variable",     b('var("KLIONS_HOME")') == 'var("%s_HOME")' % NB)
j("constant",                 b("KLIONS_VERSION") == NB + "_VERSION")
j("Rust का type (CamelCase)", b("enum KlionsError") == "enum %sError" % NC)
j("बड़े अक्षरों वाला नाम",      b("# KLIONS") == "# " + NB)
j("छोटे अक्षरों वाला नाम",     b("klions एक भाषा है") == N + " एक भाषा है")
j("बनी हुई library",          b("libklions.so") == "lib%s.so" % N)
j("लंबा extension",           b('"main.klions"') == '"main.%s"' % EXT)
j("छोटा extension",           b('"main.kl"') == '"main.%s"' % EXTC)
j("quote में अकेला kl",       b('EXT: &str = "kl";') == 'EXT: &str = "%s";' % EXTC)
j("glob वाला *.kl",           b("**/*.kl") == "**/*." + EXTC)
j("URL में भी बदला",
  b("https://klions-lang.org") == "https://%s-lang.org" % N)

# जो नहीं बदलना चाहिए
j("'kl' किसी शब्द के बीच नहीं बदला", b("klass.klx") == "klass.klx")
j("'.klang' नहीं छुआ",       b("file.klang") == "file.klang")
j("बाक़ी code नहीं छुआ",
  b("let x = 5; // कुछ और") == "let x = 5; // कुछ और")

# नाम बदलना
j("folder का नाम",  nap.badlo_naam("klions-lexer") == N + "-lexer")
j("binary का नाम",  nap.badlo_naam("klionsc") == BIN)
j("file का extension", nap.badlo_naam("xor.klions") == "xor." + EXT)
j("छोटा extension वाला नाम", nap.badlo_naam("mnist.kl") == "mnist." + EXTC)

# जोखिम की रिपोर्ट
_, _, jokhim = nap.badlo_text('pub const EXT: &str = "kl";')
j("जोखिम वाला बदलाव रिपोर्ट हुआ", len(jokhim) == 1)
_, _, jokhim2 = nap.badlo_text("use klions_ir::Mir;")
j("पक्का बदलाव जोखिम में नहीं गिना", len(jokhim2) == 0)

# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  २. नामकरण — पूरे workspace पर")
print("=" * 64)

tmp = tempfile.mkdtemp()
ws = nakli_workspace.banao(os.path.join(tmp, "klions"))
out = os.path.join(tmp, N)

# दिखाने वाला चक्कर कुछ न बदले
h0 = nap.chalo(ws, karo=False)
j("दिखाने वाला चक्कर चला", h0 is not None and h0["badlav"] > 100)
j("दिखाने वाले चक्कर में कुछ नहीं बदला",
  os.path.exists(os.path.join(ws, "crates", "klions-lexer")))

h = nap.chalo(ws, karo=True, nakal=out)
j("नक़ल बनी", h is not None and os.path.isdir(out))
j("असली folder छुआ नहीं गया",
  os.path.exists(os.path.join(ws, "crates", "klions-lexer")))

j("सारे 13 crates के नाम बदले",
  len([d for d in os.listdir(os.path.join(out, "crates"))
       if d.startswith(N)]) == 13)
j("compiler का crate %s बना" % BIN,
  os.path.isdir(os.path.join(out, "crates", BIN)))
j("उदाहरण की files का extension बदला",
  sorted(os.listdir(os.path.join(out, "examples"))) ==
  sorted(["mnist." + EXTC, "xor." + EXT]))

bacha = nap.bacha_hua_dhoondo(out)
j("कहीं 'klions' नहीं बचा (0 मिले)", len(bacha) == 0)
if bacha:
    for r, n, l in bacha[:5]:
        print("        बचा:", r, n, l)

# सामग्री सही बदली
with open(os.path.join(out, "crates", N + "-ir", "src", "lib.rs"),
          encoding="utf-8") as f:
    lib = f.read()
j("use सही बदला", "use %s_lexer::Token;" % N in lib)
j("type सही बदला", "pub enum %sError" % NC in lib)
j("env var सही बदला", 'var("%s_HOME")' % NB in lib)
j("छोटा extension सही बदला", 'EXT_SHORT: &str = "%s"' % EXTC in lib)

with open(os.path.join(out, "Cargo.toml"), encoding="utf-8") as f:
    ct = f.read()
j("workspace की members बदलीं", '"crates/%s"' % BIN in ct)
j("पुरानी members नहीं बचीं", "klions" not in ct)

with open(os.path.join(out, "crates", BIN, "Cargo.toml"),
          encoding="utf-8") as f:
    cc = f.read()
j("निर्भरता का रास्ता बदला", '"../%s-lexer"' % N in cc)

with open(os.path.join(out, "editors", "vscode", "package.json"),
          encoding="utf-8") as f:
    pj = f.read()
j("VS Code extension बदली",
  ('".%s"' % EXT) in pj and ('".%s"' % EXTC) in pj and "klions" not in pj)

j("target/ छुआ नहीं गया (नक़ल में आया ही नहीं)",
  not os.path.exists(os.path.join(out, "target")))

# दोबारा चलाने पर कुछ न बिगड़े
h2 = nap.chalo(out, karo=True)
j("दोबारा चलाने पर कुछ नहीं बदला (सुरक्षित है)", h2["badlav"] == 0)

# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  ३. मंडल भंडार")
print("=" * 64)

bj = tempfile.mkdtemp()
mb = MandalaBhandar(bj, "0.1.0")

k1 = mb.kunji("module-ir", "main.src", {"sha": "aaa"})
k2 = mb.kunji("module-ir", "main.src", {"sha": "bbb"})
j("file बदलने पर कुंजी बदली", k1 != k2)
j("निर्भरता का क्रम मायने नहीं रखता",
  mb.kunji("module-ir", "m", {"a": "1", "b": "2"}) ==
  mb.kunji("module-ir", "m", {"b": "2", "a": "1"}))

mb.rakho("module-ir", k1, {"ir": "add"})
j("रखी हुई चीज़ मिली", mb.lo("module-ir", k1)["ir"] == "add")
j("बदली कुंजी पर पुराना नहीं मिला", mb.lo("module-ir", k2) is None)

j("keyword बिंदु में गया", BINDU in mb._rasta("keyword-table", "x"))
j("निर्भरता वलय-1 में गई", VALAYA_1 in mb._rasta("dep-ir", "x"))
j("module वलय-2 में गया", VALAYA_2 in mb._rasta("module-ir", "x"))
j("macro वलय-3 में गया", VALAYA_3 in mb._rasta("macro-expand", "x"))
j("अनजान प्रकार सबसे बाहर गया",
  VALAYA_3 in mb._rasta("kuchh-naya", "x"))

kt = mb.kunji("macro-expand", "बार-बार")
mb.rakho("macro-expand", kt, {"x": 1})
for i in range(6):
    mb.lo("macro-expand", kt)
j("बार-बार काम आने वाली चीज़ अंदर चढ़ी", mb.chadhao(5) >= 1)
j("चढ़ने के बाद पुरानी जगह ख़ाली", mb.lo("macro-expand", kt) is None)

km = mb.kunji("macro-expand", "एक बार")
mb.rakho("macro-expand", km, {"x": 2})
mb.lo("macro-expand", km)
j("एक-दो बार वाली चीज़ नहीं चढ़ी", mb.chadhao(5) == 0)

kb = mb.kunji("keyword-table", "v")
mb.rakho("keyword-table", kb, {"kw": ["model"]})
kd = mb.kunji("dep-ir", "pkg")
mb.rakho("dep-ir", kd, {"ir": "महँगा"})
mb2 = MandalaBhandar(bj, "0.2.0")
j("नए compiler पर बिंदु साफ़ हुआ", mb2.lo("keyword-table", kb) is None)
j("नए compiler पर महँगा dep विश्लेषण बचा",
  mb2.lo("dep-ir", kd) is not None)

h = mb2.haal()
j("बिंदु कभी नहीं मिटता", h[BINDU]["aayu_din"] is None)
j("वलय-1 कभी नहीं मिटता", h[VALAYA_1]["aayu_din"] is None)
j("वलय-2 की उम्र 90 दिन", h[VALAYA_2]["aayu_din"] == 90)
j("वलय-3 की उम्र 3 दिन", h[VALAYA_3]["aayu_din"] == 3)

# पुरानी चीज़ मिटती है
import time
kp = mb2.kunji("macro-expand", "पुराना")
r = mb2.rakho("macro-expand", kp, {"x": 3})
purana_samay = time.time() - (4 * 24 * 60 * 60)
os.utime(r, (purana_samay, purana_samay))
mite, bache = mb2.safai()
j("3 दिन पुरानी चीज़ मिट गई", mite >= 1)
j("मिटने के बाद नहीं मिलती", mb2.lo("macro-expand", kp) is None)
j("बिंदु और वलय-1 सफ़ाई में नहीं गए",
  mb2.lo("dep-ir", kd) is not None)

# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  नतीजा:  %d पास,  %d फेल" % (paas, fail))
print("=" * 64)
if fail:
    print("\n  कुछ जाँच फेल हुई. ठीक करो.\n")
    sys.exit(1)
print("\n  सब ठीक है.\n")
