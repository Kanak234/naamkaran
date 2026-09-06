#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
नामकरण (NAAMKARAN) — KLIONS को SŪTRA बनाने वाला औज़ार.

चलाओ:

    python3 tools/naamkaran.py /रास्ता/klions
        सिर्फ़ दिखाएगा कि क्या-क्या बदलेगा. कुछ बदलेगा नहीं.
        पहले हमेशा यही चलाओ.

    python3 tools/naamkaran.py /रास्ता/klions --karo
        असल में बदलेगा.

    python3 tools/naamkaran.py /रास्ता/klions --karo --nakal /रास्ता/sutra
        असली folder छुए बिना, नई जगह बदली हुई नक़ल बनाएगा.
        सबसे सुरक्षित तरीक़ा — यही इस्तेमाल करो.

यह ऐसा क्यों — एक sed क्यों काफ़ी नहीं:
    'klions' codebase में कम से कम आठ शक्लों में छिपा होता है, और हर एक
    का बदलने का तरीक़ा अलग है:

        klions-lexer   crate का नाम, dash के साथ    -> sutra-lexer
        klions_lexer   library का नाम, underscore   -> sutra_lexer
        KLIONS_HOME    environment variable          -> SUTRA_HOME
        KlionsError    Rust का type, CamelCase       -> SutraError
        klionsc        compiler का binary            -> sutrac
        .klions / .kl  file extension                -> .sutra / .su
        libklions.so   बनी हुई library               -> libsutra.so
        "KLIONS"       docs और strings में            -> "SŪTRA"

    सादा find-replace इनमें से कुछ को ठीक करेगा और कुछ को तोड़ देगा.
    ख़ास तौर पर 'klionsc' — अगर पहले 'klions' -> 'sutra' चला दिया, तो
    'klionsc' बन जाएगा 'sutrac'... जो सही है. पर 'klions_compiler'
    बन जाएगा 'sutra_compiler', जो शायद तुम नहीं चाहते.

    इसलिए यहाँ बदलाव **क्रम में** होते हैं — सबसे लंबा और ख़ास पहले,
    सबसे आम सबसे बाद में. यही पूरे औज़ार की जान है.

क्या नहीं छुआ जाएगा:
    target/, .git/, node_modules/ — इनमें बनी हुई चीज़ें हैं. उन्हें
    बदलना बेकार भी है और ख़तरनाक भी (binary files में बदलाव उन्हें
    तोड़ देता है). ये दोबारा बन जाएँगी.
"""

import argparse
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# बदलाव की सूची — क्रम मायने रखता है, ऊपर वाला पहले चलेगा
#
# नियम: सबसे लंबा और सबसे ख़ास पहले. आम सबसे बाद में.
#
# सोचो कि तुम 'klionsc' बदलना चाहते हो. अगर पहले 'klions' -> 'sutra'
# चला दिया, तो तुम्हारे पास 'sutrac' बचेगा — इस बार सही है, पर हमेशा
# नहीं. 'klions_home' पहले चला तो 'KLIONS_HOME' छूट जाएगा क्योंकि उसका
# case अलग है. इसलिए हर शक्ल अपनी बारी से, और आम वाली आख़िर में.
# ---------------------------------------------------------------------------
def badlav_banao(naya_naam, naya_ext, naya_ext_chhota, naya_binary):
    """
    बदलावों की सूची बनाता है — किसी भी नए नाम के लिए.

    पहले यह सूची जमी हुई थी, सीधे 'sutra' पर. वो ग़लती थी, और वो जाँच में
    नहीं बल्कि ज़िंदगी में पकड़ी गई: नाम पहले से लिया हुआ निकला, और तब
    पता चला कि औज़ार दूसरा नाम ले ही नहीं सकता.

    सबक़ यह कि नाम एक ऐसी चीज़ है जो बदल सकती है — इसलिए उसे code में
    जमाना नहीं चाहिए. अब नाम बाहर से आता है.

    क्रम अब भी वही: सबसे लंबा और ख़ास पहले, सबसे आम सबसे बाद में.
    """
    N = naya_naam.lower()          # जैसे 'nirukta'
    NB = naya_naam.upper()         # जैसे 'NIRUKTA'
    NC = naya_naam.capitalize()    # जैसे 'Nirukta'

    return [
        # 1. compiler का binary — सबसे ख़ास, इसलिए सबसे पहले
        ("klionsc", naya_binary),
        ("KlionsC", NC + "C"),

        # 2. बनी हुई library के नाम
        ("libklions", "lib" + N),

        # 3. environment variables और constants (सब बड़े अक्षर)
        ("KLIONS_", NB + "_"),

        # 4. file extension — लंबा पहले, छोटा बाद में
        (".klions", "." + naya_ext),

        # 5. crate और library के नाम
        ("klions-", N + "-"),
        ("klions_", N + "_"),

        # 6. Rust के types — CamelCase
        ("Klions", NC),

        # 7. सबसे आम — सबसे आख़िर में
        ("KLIONS", NB),
        ("klions", N),
    ]


# default — बदलने के लिए naamkaran.py को --naya-naam दो
NAYA_NAAM = "nirukta"
NAYA_EXT = "nirukta"
NAYA_EXT_CHHOTA = "nir"
NAYA_BINARY = "niruktac"

BADLAV = badlav_banao(NAYA_NAAM, NAYA_EXT, NAYA_EXT_CHHOTA, NAYA_BINARY)


# '.kl' अलग
# '.kl' अलग से क्यों:
#     '.kl' बहुत छोटा है. 'file.klx', '.klang', या किसी शब्द के बीच में
#     भी मिल सकता है. इसलिए इसे सिर्फ़ तब बदला जाता है जब वो सचमुच
#     extension की जगह हो — यानी उसके बाद कुछ न हो, या quote/जगह हो.
KL_BADLAV = [
    (r'\.kl(?=["\'\s,\)\]}]|$)', "." + NAYA_EXT_CHHOTA),
]

# बिना बिंदु वाला "kl" — यह जाँच में पकड़ा गया था.
#
# constant अक्सर ऐसे लिखा होता है:  EXT_SHORT: &str = "kl"
# यहाँ बिंदु नहीं है, इसलिए ऊपर वाला नियम इसे छोड़ देता था — और वो
# एक अकेला बचा हुआ धागा महीनों बाद उलझाता, क्योंकि compiler '.su'
# फ़ाइलें बनाता पर '.kl' ढूँढता.
#
# सिर्फ़ quote के अंदर अकेला 'kl' बदला जाता है, कहीं और नहीं. फिर भी
# यह जोखिम भरा है, इसलिए हर ऐसा बदलाव नीचे 'जाँच लो' सूची में दिखता है.
JOKHIM_BADLAV = [
    (r'"kl"', '"%s"' % NAYA_EXT_CHHOTA),
    (r"'kl'", "'%s'" % NAYA_EXT_CHHOTA),
    (r'\*\.kl\b', "*." + NAYA_EXT_CHHOTA),
]

# जिन folders को छूना ही नहीं
CHHODO_FOLDER = {
    "target", ".git", "node_modules", "__pycache__", ".vscode-test",
    "dist", "build", ".cargo",
}

# जिन files को text मानकर पढ़ा जाएगा
TEXT_EXT = {
    ".rs", ".toml", ".md", ".json", ".txt", ".yaml", ".yml", ".klions",
    ".kl", ".sutra", ".su", ".sh", ".py", ".ts", ".js", ".lock", ".cfg",
    ".gitignore", ".editorconfig", ".html", ".css",
}


def text_file_hai(rasta):
    """
    यह file text है या नहीं.

    Extension से पहले जाँचते हैं, फिर सामग्री से. दोनों इसलिए कि कुछ
    ज़रूरी files के extension होते ही नहीं (LICENSE, Makefile), और
    कुछ binary files के extension text जैसे दिखते हैं.
    """
    naam = os.path.basename(rasta)
    _, ext = os.path.splitext(naam)

    if ext.lower() in TEXT_EXT:
        return True
    if naam in ("LICENSE", "Makefile", "Dockerfile", "CHANGELOG",
                ".gitignore", "rust-toolchain"):
        return True
    if ext:
        return False

    # बिना extension वाली file — शुरुआत पढ़कर देखो
    try:
        with open(rasta, "rb") as f:
            shuru = f.read(2048)
        if b"\x00" in shuru:
            return False        # शून्य byte मतलब binary
        shuru.decode("utf-8")
        return True
    except (UnicodeDecodeError, IOError, OSError):
        return False


def badlo_text(text):
    """
    एक file की सामग्री में सारे बदलाव करता है, क्रम से.

    लौटाता है: (नई_सामग्री, कितने_बदलाव, जोखिम_वाली_लाइनें)

    जोखिम वाली लाइनें अलग से लौटती हैं ताकि तुम उन्हें आँख से देख सको.
    बाक़ी बदलाव पक्के हैं; ये वाले अंदाज़े पर टिके हैं.
    """
    ginti = 0
    for purana, naya in BADLAV:
        n = text.count(purana)
        if n:
            text = text.replace(purana, naya)
            ginti += n

    for pattern, naya in KL_BADLAV:
        text, n = re.subn(pattern, naya, text)
        ginti += n

    # जोखिम वाले — बदलते भी हैं और दर्ज भी होते हैं
    jokhim = []
    for pattern, naya in JOKHIM_BADLAV:
        for i, line in enumerate(text.split("\n"), 1):
            if re.search(pattern, line):
                jokhim.append((i, line.strip()[:80]))
        text, n = re.subn(pattern, naya, text)
        ginti += n

    return text, ginti, jokhim


def badlo_naam(naam):
    """
    file या folder का नाम बदलता है.

    वही क्रम, वही नियम. सिर्फ़ नाम पर लगता है, सामग्री पर नहीं.
    """
    naya = naam
    for purana, badla in BADLAV:
        naya = naya.replace(purana, badla)
    for pattern, badla in KL_BADLAV:
        naya = re.sub(pattern, badla, naya)
    return naya


def chalo(jad, karo=False, nakal=None):
    """
    पूरा नामकरण चलाता है.

    karo=False  -> सिर्फ़ दिखाता है
    nakal=रास्ता -> असली folder छुए बिना नई जगह बदली हुई नक़ल बनाता है

    लौटाता है: हिसाब का dict
    """
    jad = os.path.abspath(jad)
    if not os.path.isdir(jad):
        print("यह folder नहीं मिला:", jad)
        return None

    # नक़ल वाला तरीक़ा — सबसे सुरक्षित, इसलिए इसे बढ़ावा दिया है
    if nakal:
        nakal = os.path.abspath(nakal)
        if os.path.exists(nakal):
            print("यह जगह पहले से भरी है:", nakal)
            print("पहले उसे हटाओ या कोई और नाम दो.")
            return None
        if karo:
            print("  नक़ल बन रही है… (target/ और .git/ छोड़कर)")
            shutil.copytree(
                jad, nakal,
                ignore=lambda d, n: [x for x in n if x in CHHODO_FOLDER])
            jad = nakal
        else:
            print("  (दिखाने वाला चक्कर — नक़ल अभी नहीं बनेगी)")

    hisaab = {
        "files_dekhi": 0, "files_badli": 0, "badlav": 0,
        "naam_badle": 0, "chhodi": 0,
    }
    badli_suchi = []
    naam_suchi = []
    jokhim_suchi = []

    # पहले सामग्री बदलो, फिर नाम.
    #
    # यह क्रम ज़रूरी है. अगर पहले नाम बदल दिए, तो जिन रास्तों पर हम
    # चल रहे हैं वो बीच में ही बदल जाएँगे और os.walk उलझ जाएगा.
    for root, dirs, files in os.walk(jad):
        dirs[:] = [d for d in dirs if d not in CHHODO_FOLDER]

        for f in files:
            poora = os.path.join(root, f)
            hisaab["files_dekhi"] += 1

            if not text_file_hai(poora):
                hisaab["chhodi"] += 1
                continue

            try:
                with open(poora, "r", encoding="utf-8") as fh:
                    purana = fh.read()
            except (UnicodeDecodeError, IOError, OSError):
                hisaab["chhodi"] += 1
                continue

            naya, n, jokhim = badlo_text(purana)
            if jokhim:
                for line_no, line in jokhim:
                    jokhim_suchi.append(
                        (os.path.relpath(poora, jad), line_no, line))
            if n == 0:
                continue

            hisaab["files_badli"] += 1
            hisaab["badlav"] += n
            badli_suchi.append((os.path.relpath(poora, jad), n))

            if karo:
                # .tmp फिर rename — बिजली जाए तो आधी file न बचे
                temp = poora + ".tmp"
                with open(temp, "w", encoding="utf-8") as fh:
                    fh.write(naya)
                os.replace(temp, poora)

    # अब नाम — नीचे से ऊपर, ताकि folder का नाम बदलने से पहले
    # उसके अंदर की files निपट जाएँ
    for root, dirs, files in os.walk(jad, topdown=False):
        if any(part in CHHODO_FOLDER for part in root.split(os.sep)):
            continue

        for naam in files + dirs:
            naya_naam = badlo_naam(naam)
            if naya_naam == naam:
                continue
            hisaab["naam_badle"] += 1
            naam_suchi.append((
                os.path.relpath(os.path.join(root, naam), jad), naya_naam))
            if karo:
                try:
                    os.rename(os.path.join(root, naam),
                              os.path.join(root, naya_naam))
                except OSError as e:
                    print("  नाम नहीं बदल सका: %s (%s)" % (naam, e))

    hisaab["_badli_suchi"] = badli_suchi
    hisaab["_naam_suchi"] = naam_suchi
    hisaab["_jokhim_suchi"] = jokhim_suchi
    hisaab["_jad"] = jad
    return hisaab


def bacha_hua_dhoondo(jad):
    """
    बदलने के बाद जाँचता है कि कहीं 'klions' बचा तो नहीं.

    यह सबसे ज़रूरी हिस्सा है. बदलाव चला देना आसान है; यह पक्का करना कि
    कुछ छूटा नहीं — वही असली काम है. एक छूटा हुआ नाम हफ़्तों बाद किसी
    अजीब जगह फूटेगा, और तब तक तुम भूल चुके होगे कि नाम बदला था.

    लौटाता है: [(file, line नंबर, line), …]
    """
    mile = []
    for root, dirs, files in os.walk(jad):
        dirs[:] = [d for d in dirs if d not in CHHODO_FOLDER]
        for f in files:
            poora = os.path.join(root, f)
            if not text_file_hai(poora):
                continue
            try:
                with open(poora, "r", encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r"klions|KLIONS|Klions", line):
                            mile.append((os.path.relpath(poora, jad),
                                         i, line.strip()[:90]))
            except (UnicodeDecodeError, IOError, OSError):
                continue

        # नामों में भी बचा हो सकता है
        for naam in files + dirs:
            if re.search(r"klions|KLIONS|Klions", naam):
                mile.append((os.path.relpath(os.path.join(root, naam), jad),
                             0, "<— file/folder का नाम>"))
    return mile


def mukhya():
    # global function की सबसे पहली लाइन पर.
    # Python इन नामों के किसी भी इस्तेमाल से पहले घोषणा माँगता है, और
    # ये argparse के default/help में भी इस्तेमाल होते हैं — इसलिए
    # बीच में लिखने पर SyntaxError आता है.
    global BADLAV, KL_BADLAV, JOKHIM_BADLAV, NAYA_EXT_CHHOTA

    p = argparse.ArgumentParser(
        description="KLIONS को SŪTRA बनाने वाला औज़ार")
    p.add_argument("jad", help="klions workspace का रास्ता")
    p.add_argument("--karo", action="store_true",
                   help="असल में बदलो (बिना इसके सिर्फ़ दिखाता है)")
    p.add_argument("--nakal", help="असली छुए बिना नई जगह नक़ल बनाओ")
    p.add_argument("--poori-suchi", action="store_true",
                   help="सारी बदली हुई files दिखाओ")
    p.add_argument("--naya-naam", default=NAYA_NAAM,
                   help="नया नाम (default: %s)" % NAYA_NAAM)
    p.add_argument("--naya-ext", default=None,
                   help="नया extension (default: नाम जैसा)")
    p.add_argument("--naya-ext-chhota", default=NAYA_EXT_CHHOTA,
                   help="छोटा extension (default: %s)" % NAYA_EXT_CHHOTA)
    p.add_argument("--naya-binary", default=None,
                   help="compiler का binary (default: नाम + c)")
    a = p.parse_args()

    ext = a.naya_ext or a.naya_naam.lower()
    binary = a.naya_binary or (a.naya_naam.lower() + "c")
    NAYA_EXT_CHHOTA = a.naya_ext_chhota
    BADLAV = badlav_banao(a.naya_naam, ext, NAYA_EXT_CHHOTA, binary)
    KL_BADLAV = [(r'\.kl(?=["\'\s,\)\]}]|$)', "." + NAYA_EXT_CHHOTA)]
    JOKHIM_BADLAV = [
        (r'"kl"', '"%s"' % NAYA_EXT_CHHOTA),
        (r"'kl'", "'%s'" % NAYA_EXT_CHHOTA),
        (r'\*\.kl\b', "*." + NAYA_EXT_CHHOTA),
    ]

    print()
    print("  नामकरण — KLIONS  ->  %s" % a.naya_naam.upper())
    print("  " + "=" * 60)
    if not a.karo:
        print("  (सिर्फ़ दिखाने वाला चक्कर — कुछ बदलेगा नहीं)")
    print()

    h = chalo(a.jad, a.karo, a.nakal)
    if h is None:
        return 1

    print("  files देखीं      : %d" % h["files_dekhi"])
    print("  files बदलीं     : %d" % h["files_badli"])
    print("  कुल बदलाव       : %d" % h["badlav"])
    print("  नाम बदले        : %d" % h["naam_badle"])
    print("  छोड़ी (binary)   : %d" % h["chhodi"])
    print()

    kitni = len(h["_badli_suchi"]) if a.poori_suchi else 12
    if h["_badli_suchi"]:
        print("  बदली हुई files:")
        for rasta, n in h["_badli_suchi"][:kitni]:
            print("     %4d  %s" % (n, rasta))
        if len(h["_badli_suchi"]) > kitni:
            print("     … और %d files (--poori-suchi से सब देखो)"
                  % (len(h["_badli_suchi"]) - kitni))
        print()

    if h["_naam_suchi"]:
        print("  नाम बदले:")
        for purana, naya in h["_naam_suchi"][:kitni]:
            print("     %s  ->  %s" % (purana, naya))
        if len(h["_naam_suchi"]) > kitni:
            print("     … और %d" % (len(h["_naam_suchi"]) - kitni))
        print()

    if h["_jokhim_suchi"]:
        print("  जाँच लो — ये बदलाव अंदाज़े पर हुए हैं:")
        for rasta, line_no, line in h["_jokhim_suchi"][:12]:
            print("     %s:%d  %s" % (rasta, line_no, line))
        if len(h["_jokhim_suchi"]) > 12:
            print("     … और %d" % (len(h["_jokhim_suchi"]) - 12))
        print("  (अकेला \"kl\" — लगभग हमेशा extension होता है, पर देख लो)")
        print()

    if a.karo:
        print("  बचा हुआ ढूँढ रहा हूँ…")
        bacha = bacha_hua_dhoondo(h["_jad"])
        if bacha:
            print()
            print("  >>> ध्यान: %d जगह 'klions' अब भी बचा है:" % len(bacha))
            for rasta, line_no, line in bacha[:15]:
                if line_no:
                    print("      %s:%d  %s" % (rasta, line_no, line))
                else:
                    print("      %s  %s" % (rasta, line))
            if len(bacha) > 15:
                print("      … और %d" % (len(bacha) - 15))
            print()
            print("  ये हाथ से देखो. हो सकता है ये जान-बूझकर हों")
            print("  (जैसे CHANGELOG में पुराने नाम का ज़िक्र).")
        else:
            print("  कहीं कुछ नहीं बचा. नामकरण पूरा.")
        print()
        print("  अब यह चलाओ:")
        print("      cd %s" % h["_jad"])
        print("      cargo build")
        print("      cargo test")
        print()
        print("  cargo test 179 पास दिखाए, तभी मानना कि काम हुआ.")
    else:
        print("  असल में बदलने के लिए --karo लगाओ.")
        print("  और सुरक्षित तरीक़ा:  --karo --nakal /रास्ता/sutra")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(mukhya())
