# -*- coding: utf-8 -*-
"""
मंडल भंडार (MANDALA BHANDAR) — sutrac का incremental build cache.

यह क्या है:
    Compiler जो चीज़ें दोबारा बना सकता है, उन्हें फेंकने के बजाय
    सँभालकर रखता है — पर सब कुछ हमेशा के लिए नहीं.

    चारों वलय वही हैं जो ABHYAS और SABHA में हैं, बस यहाँ 'कितनी तेज़ी
    से बदलता है' का मतलब compiler की भाषा में है:

        बिंदु    भाषा की अपनी चीज़ें — keywords, builtin types, prelude.
                 ये तभी बदलती हैं जब compiler का version बदले.
                 कभी अपने आप नहीं मिटतीं.

        वलय-1    बाहरी packages का विश्लेषण. एक बार बना, महीनों चला.
                 तुम अपना code रोज़ बदलते हो; निर्भरताएँ साल में दो बार.
                 कभी अपने आप नहीं मिटतीं.

        वलय-2    तुम्हारे अपने modules का IR और types.
                 file बदलने पर उसी का हिस्सा बेकार होता है, बाक़ी बचता है.
                 90 दिन.

        वलय-3    इसी बार की चीज़ें — फैलाए हुए macro, अस्थायी IR.
                 अगले build तक भी शायद न चाहिए हों. 3 दिन.

यह ऐसा क्यों — cargo की तरह सब एक जगह क्यों नहीं:
    क्योंकि सब एक जगह रखने पर 'cargo clean' ही अकेला रास्ता बचता है, और
    वो सब कुछ फेंक देता है — निर्भरताओं का वो विश्लेषण भी जो बीस मिनट में
    बना था और जिसमें कोई गड़बड़ थी ही नहीं.

    परतों में बाँटने से तुम सिर्फ़ वो परत फेंक सकते हो जो सचमुच बासी है.
    वलय-3 रोज़ अपने आप जाता है. वलय-1 सालों बैठा रहता है. यही असली बचत है.

    और एक बात — यह अपने आप घटता रहता है. तुम्हें कभी यह फ़ैसला नहीं लेना
    पड़ता कि क्या मिटाना है. बाहरी परत उम्र पूरी करके ख़ुद चली जाती है,
    और जो सचमुच काम आ रहा है वो अंदर चढ़कर बचा रहता है.

यह sutrac से कैसे जुड़ेगा:
    यह Python में है और compiler Rust में — इसलिए यह चलने वाला code
    नहीं, ढाँचे का नमूना है. Folder की शक्ल, कुंजी बनाने का तरीक़ा,
    उम्र के नियम और चढ़ने का नियम — ये सब यहाँ तय हो चुके हैं, और इन्हें
    Rust में उतारना सीधा है.

    जाँच नीचे चलती है, इसलिए नियम सिर्फ़ काग़ज़ पर नहीं हैं.
"""

import hashlib
import json
import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

BINDU = "bindu"
VALAYA_1 = "valaya-1"
VALAYA_2 = "valaya-2"
VALAYA_3 = "valaya-3"

# हर वलय की उम्र, दिनों में. None = कभी नहीं मिटता.
AAYU_DIN = {
    BINDU: None,
    VALAYA_1: None,
    VALAYA_2: 90,
    VALAYA_3: 3,
}

# कौन सी चीज़ किस वलय में जाती है.
#
# यह नक़्शा ही पूरा फ़ैसला है. कोई नई चीज़ cache करनी हो तो यहाँ एक
# लाइन जोड़ो — बाक़ी सब अपने आप काम करेगा.
KAHAN = {
    "keyword-table": BINDU,
    "builtin-types": BINDU,
    "prelude-ir": BINDU,

    "dep-metadata": VALAYA_1,
    "dep-ir": VALAYA_1,
    "dep-symbols": VALAYA_1,

    "module-ir": VALAYA_2,
    "module-types": VALAYA_2,
    "module-symbols": VALAYA_2,
    "borrowck": VALAYA_2,

    "macro-expand": VALAYA_3,
    "temp-ir": VALAYA_3,
    "diagnostics": VALAYA_3,
}


class MandalaBhandar(object):
    """sutrac का भंडार."""

    def __init__(self, jad, sutrac_version="0.1.0"):
        """
        jad = भंडार का folder, आम तौर पर <project>/.sutra/mandala
        sutrac_version = compiler का version

        Version यहाँ इसलिए चाहिए कि बिंदु की चीज़ें compiler के साथ
        बँधी होती हैं. नया compiler आया तो पुराना बिंदु बेकार — और वो
        अपने आप साफ़ होना चाहिए, वरना नया compiler पुरानी keyword-table
        पढ़ेगा और गड़बड़ बहुत गहरी होगी.
        """
        self.jad = jad
        self.version = sutrac_version
        for v in (BINDU, VALAYA_1, VALAYA_2, VALAYA_3):
            os.makedirs(os.path.join(jad, v), exist_ok=True)
        self._version_jaancho()

    def _version_jaancho(self):
        """compiler बदला हो तो बिंदु साफ़ करो."""
        nishan = os.path.join(self.jad, BINDU, ".version")
        purana = None
        if os.path.exists(nishan):
            try:
                with open(nishan, "r", encoding="utf-8") as f:
                    purana = f.read().strip()
            except (IOError, OSError):
                pass

        if purana and purana != self.version:
            # बिंदु compiler से बँधा है — नया compiler, नया बिंदु.
            # वलय-1 को नहीं छूते: निर्भरताओं का विश्लेषण compiler के
            # छोटे version बदलने से बेकार नहीं होता, और वही सबसे महँगा है.
            b = os.path.join(self.jad, BINDU)
            shutil.rmtree(b, ignore_errors=True)
            os.makedirs(b, exist_ok=True)

        try:
            with open(nishan, "w", encoding="utf-8") as f:
                f.write(self.version)
        except (IOError, OSError):
            pass

    # -- कुंजी ------------------------------------------------------------------

    def kunji(self, prakar, pehchan, nirbharta=None):
        """
        cache की कुंजी बनाता है.

        prakar     = ऊपर KAHAN में से कोई एक
        pehchan    = किस चीज़ की — file का रास्ता, module का नाम
        nirbharta  = जिन चीज़ों पर यह टिकी है उनकी छाप (sha, mtime, flags)

        निर्भरता कुंजी में क्यों घुसती है — यही पूरे cache की जान है.
        अगर कुंजी सिर्फ़ file के नाम से बने, तो file बदलने पर पुराना
        नतीजा लौटता रहेगा. निर्भरता की छाप कुंजी में हो, तो कुछ भी
        बदलने पर कुंजी अपने आप बदल जाती है और पुराना अपने आप बेकार
        हो जाता है.

        यानी cache invalidation अलग से करनी ही नहीं पड़ती. वो कुंजी के
        बनने के तरीक़े से अपने आप हो जाती है.
        """
        h = hashlib.sha256()
        h.update(prakar.encode("utf-8"))
        h.update(b"\x00")
        h.update(pehchan.encode("utf-8"))
        if nirbharta:
            for k in sorted(nirbharta):
                h.update(b"\x00")
                h.update(("%s=%s" % (k, nirbharta[k])).encode("utf-8"))
        return h.hexdigest()[:24]

    def _rasta(self, prakar, kunji):
        valaya = KAHAN.get(prakar, VALAYA_3)
        # पहले दो अक्षर से उप-folder — एक folder में लाखों files
        # रखने पर हर listing धीमी हो जाती है
        return os.path.join(self.jad, valaya, prakar,
                            kunji[:2], kunji + ".json")

    # -- रखना और लेना -------------------------------------------------------------

    def rakho(self, prakar, kunji, samagri):
        """cache में डालो."""
        rasta = self._rasta(prakar, kunji)
        os.makedirs(os.path.dirname(rasta), exist_ok=True)
        record = {
            "prakar": prakar, "kunji": kunji,
            "rakha": time.time(), "chhua": time.time(),
            "kitni_baar": 0, "samagri": samagri,
        }
        temp = rasta + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(temp, rasta)
        return rasta

    def lo(self, prakar, kunji):
        """
        cache से निकालो. न मिले तो None.

        निकालते वक़्त 'kitni_baar' बढ़ता है और 'chhua' का समय ताज़ा होता है.
        यही दो चीज़ें बाद में तय करती हैं कि यह record अंदर चढ़ने लायक है
        या बाहरी परत के साथ जाने लायक.
        """
        rasta = self._rasta(prakar, kunji)
        if not os.path.exists(rasta):
            return None
        try:
            with open(rasta, "r", encoding="utf-8") as f:
                record = json.load(f)
        except (ValueError, IOError, OSError):
            try:
                os.remove(rasta)      # ख़राब record बार-बार न अटकाए
            except OSError:
                pass
            return None

        record["chhua"] = time.time()
        record["kitni_baar"] = record.get("kitni_baar", 0) + 1
        try:
            with open(rasta, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
        except (IOError, OSError):
            pass
        return record["samagri"]

    # -- चढ़ना ---------------------------------------------------------------------

    def chadhao(self, kam_se_kam_baar=5):
        """
        जो चीज़ें बार-बार काम आईं, उन्हें एक वलय अंदर चढ़ा देता है.

        यही 'जो काम आया वो बचता है' वाला नियम है. वलय-3 की कोई चीज़ अगर
        पाँच बार काम आई, तो वो अस्थायी नहीं रह गई — उसे वलय-2 में चढ़ा दो,
        जहाँ वो 3 दिन के बजाय 90 दिन बचेगी.

        फ़ायदा यह कि तुम्हें पहले से तय नहीं करना पड़ता कि क्या ज़रूरी है.
        इस्तेमाल ख़ुद बता देता है.

        लौटाता है: कितनी चीज़ें चढ़ीं
        """
        chadhe = 0
        for se, tak in ((VALAYA_3, VALAYA_2), (VALAYA_2, VALAYA_1)):
            se_folder = os.path.join(self.jad, se)
            if not os.path.isdir(se_folder):
                continue
            for prakar in os.listdir(se_folder):
                p_folder = os.path.join(se_folder, prakar)
                if not os.path.isdir(p_folder):
                    continue
                for up in os.listdir(p_folder):
                    up_folder = os.path.join(p_folder, up)
                    if not os.path.isdir(up_folder):
                        continue
                    for f in os.listdir(up_folder):
                        if not f.endswith(".json"):
                            continue
                        poora = os.path.join(up_folder, f)
                        try:
                            with open(poora, "r", encoding="utf-8") as fh:
                                r = json.load(fh)
                        except (ValueError, IOError, OSError):
                            continue
                        if r.get("kitni_baar", 0) < kam_se_kam_baar:
                            continue
                        naya = os.path.join(self.jad, tak, prakar, up, f)
                        os.makedirs(os.path.dirname(naya), exist_ok=True)
                        try:
                            os.replace(poora, naya)
                            chadhe += 1
                        except OSError:
                            pass
        return chadhe

    # -- सफ़ाई ----------------------------------------------------------------------

    def safai(self):
        """
        उम्र पूरी कर चुकी चीज़ें मिटाता है.

        हर build के बाद चलना चाहिए. सस्ता है — सिर्फ़ mtime देखता है,
        file खोलता नहीं.

        लौटाता है: (कितनी मिटीं, कितने byte बचे)
        """
        mite = 0
        bache = 0
        ab = time.time()
        for valaya, din in AAYU_DIN.items():
            if din is None:
                continue
            seema = din * 24 * 60 * 60
            folder = os.path.join(self.jad, valaya)
            if not os.path.isdir(folder):
                continue
            for root, dirs, files in os.walk(folder):
                for f in files:
                    poora = os.path.join(root, f)
                    try:
                        # chhua नहीं, mtime — क्योंकि lo() हर बार file
                        # दोबारा लिखता है, इसलिए mtime अपने आप 'आख़िरी
                        # इस्तेमाल' बन जाता है. एक ही चीज़ दो जगह रखने
                        # से बचे.
                        if ab - os.path.getmtime(poora) > seema:
                            bache += os.path.getsize(poora)
                            os.remove(poora)
                            mite += 1
                    except OSError:
                        pass
        return mite, bache

    # -- हाल ------------------------------------------------------------------------

    def haal(self):
        """हर वलय में कितना है."""
        out = {}
        for valaya in (BINDU, VALAYA_1, VALAYA_2, VALAYA_3):
            folder = os.path.join(self.jad, valaya)
            ginti = 0
            naap = 0
            if os.path.isdir(folder):
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        if not f.endswith(".json"):
                            continue
                        ginti += 1
                        try:
                            naap += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass
            out[valaya] = {"ginti": ginti, "kb": round(naap / 1024.0, 1),
                           "aayu_din": AAYU_DIN[valaya]}
        return out


# ---------------------------------------------------------------------------
# जाँच: python3 mandala/mandala_bhandar.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    jad = tempfile.mkdtemp()
    b = MandalaBhandar(jad, "0.1.0")

    # कुंजी निर्भरता से बदलती है
    k1 = b.kunji("module-ir", "src/main.sutra", {"sha": "aaa", "opt": "2"})
    k2 = b.kunji("module-ir", "src/main.sutra", {"sha": "bbb", "opt": "2"})
    k3 = b.kunji("module-ir", "src/main.sutra", {"sha": "aaa", "opt": "3"})
    assert k1 != k2, "file बदलने पर कुंजी नहीं बदली"
    assert k1 != k3, "flag बदलने पर कुंजी नहीं बदली"
    assert k1 == b.kunji("module-ir", "src/main.sutra",
                         {"opt": "2", "sha": "aaa"}), "क्रम से कुंजी बदल गई"

    # रखना-लेना
    b.rakho("module-ir", k1, {"ir": "%1 = add i32 %a, %b"})
    assert b.lo("module-ir", k1)["ir"].startswith("%1")
    assert b.lo("module-ir", k2) is None, "बदली कुंजी पर पुराना मिला"

    # सही वलय में गया या नहीं
    assert os.path.exists(b._rasta("module-ir", k1))
    assert VALAYA_2 in b._rasta("module-ir", k1)
    assert BINDU in b._rasta("keyword-table", "x")
    assert VALAYA_1 in b._rasta("dep-ir", "x")
    assert VALAYA_3 in b._rasta("macro-expand", "x")
    assert VALAYA_3 in b._rasta("koi-anjaan-prakar", "x"), \
        "अनजान प्रकार सबसे बाहरी वलय में जाना चाहिए"

    # चढ़ना
    kt = b.kunji("macro-expand", "बार-बार वाला")
    b.rakho("macro-expand", kt, {"x": 1})
    for i in range(6):
        b.lo("macro-expand", kt)
    chadhe = b.chadhao(kam_se_kam_baar=5)
    assert chadhe >= 1, "बार-बार काम आने वाली चीज़ चढ़ी नहीं"
    assert b.lo("macro-expand", kt) is None, \
        "चढ़ने के बाद पुरानी जगह से भी मिल रहा है"

    # version बदलने पर बिंदु साफ़, वलय-1 बचा
    kb = b.kunji("keyword-table", "v1")
    b.rakho("keyword-table", kb, {"kw": ["model", "train", "tensor"]})
    kd = b.kunji("dep-ir", "koi-package")
    b.rakho("dep-ir", kd, {"ir": "बहुत महँगा विश्लेषण"})
    assert b.lo("keyword-table", kb) is not None

    b2 = MandalaBhandar(jad, "0.2.0")
    assert b2.lo("keyword-table", kb) is None, \
        "नए compiler पर पुराना बिंदु बचा रह गया"
    assert b2.lo("dep-ir", kd) is not None, \
        "version बदलने पर महँगा dep विश्लेषण भी फेंक दिया"

    h = b2.haal()
    assert h[BINDU]["aayu_din"] is None
    assert h[VALAYA_3]["aayu_din"] == 3

    mite, bache = b2.safai()
    print("मंडल भंडार ठीक है — सारी जाँच पास.")
    print("हाल:")
    for v, d in b2.haal().items():
        print("   %-10s %3d चीज़ें  %6.1f KB  उम्र: %s" % (
            v, d["ginti"], d["kb"],
            "हमेशा" if d["aayu_din"] is None else "%d दिन" % d["aayu_din"]))
