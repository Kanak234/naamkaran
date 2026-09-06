# -*- coding: utf-8 -*-
"""
nakli_workspace.py — नक़ली KLIONS workspace बनाता है, जाँच के लिए.

यह क्यों:
    नामकरण का औज़ार तुम्हारे असली codebase पर चलेगा. उसे बिना जाँचे भेजना
    ग़लत होगा — एक ग़लत बदलाव 13 crates को तोड़ सकता है, और वो टूट हफ़्तों
    बाद किसी अजीब जगह दिखेगी.

    इसलिए यहाँ एक ऐसा workspace बनाया गया है जिसमें वो हर शक्ल मौजूद है
    जिसमें 'klions' असली codebase में छिपा हो सकता है:

        klions            सादा नाम
        klions_ir         underscore वाला crate
        klions-lexer      dash वाला crate
        KLIONS_HOME       environment variable
        KlionsError       Rust का type
        KLIONS_VERSION    constant
        .klions / .kl     file extension
        libklions.so      बनी हुई library
        klionsc           compiler का binary
        "klions"          strings और docs में

    असली folder पर चलाने से पहले औज़ार इन सब पर सही निकलना चाहिए.
"""

import os
import shutil

# 13 crates — असली workspace जैसी शक्ल
CRATES = [
    "klions-lexer", "klions-parser", "klions-ast", "klions-ir",
    "klions-typeck", "klions-borrowck", "klions-interp", "klions-codegen",
    "klions-runtime", "klions-tensor", "klions-autodiff", "klions-lsp",
    "klionsc",
]


def banao(jad):
    """नक़ली workspace बनाता है और उसका रास्ता लौटाता है."""
    if os.path.exists(jad):
        shutil.rmtree(jad)
    os.makedirs(jad)

    # ऊपर वाली Cargo.toml
    with open(os.path.join(jad, "Cargo.toml"), "w", encoding="utf-8") as f:
        f.write("[workspace]\nresolver = \"2\"\nmembers = [\n")
        for c in CRATES:
            f.write('    "crates/%s",\n' % c)
        f.write("]\n\n[workspace.package]\n")
        f.write('version = "0.1.0"\n')
        f.write('authors = ["Kanak Prabhakar"]\n')

    for c in CRATES:
        crate_dir = os.path.join(jad, "crates", c, "src")
        os.makedirs(crate_dir)

        lib_naam = c.replace("-", "_")
        with open(os.path.join(jad, "crates", c, "Cargo.toml"), "w",
                  encoding="utf-8") as f:
            f.write("[package]\n")
            f.write('name = "%s"\n' % c)
            f.write("version.workspace = true\n\n")
            f.write("[dependencies]\n")
            if c != "klions-lexer":
                f.write('klions-lexer = { path = "../klions-lexer" }\n')
            if c in ("klionsc", "klions-lsp"):
                f.write('klions-ir = { path = "../klions-ir" }\n')
                f.write('klions-parser = { path = "../klions-parser" }\n')
            f.write("\n[lib]\n")
            f.write('name = "%s"\n' % lib_naam)

        with open(os.path.join(crate_dir, "lib.rs"), "w",
                  encoding="utf-8") as f:
            f.write("//! %s — KLIONS का हिस्सा\n" % c)
            f.write("//! देखो: https://klions-lang.org/docs/%s\n\n" % lib_naam)
            f.write("use klions_lexer::Token;\n")
            if c in ("klionsc", "klions-lsp"):
                f.write("use klions_ir::Mir;\n")
                f.write("use klions_parser::Parser;\n")
            f.write("\npub const KLIONS_VERSION: &str = \"0.1.0\";\n")
            f.write("pub const KLIONS_EXT: &str = \"klions\";\n")
            f.write("pub const KLIONS_EXT_SHORT: &str = \"kl\";\n\n")
            f.write("#[derive(Debug)]\npub enum KlionsError {\n")
            f.write("    Lex(String),\n    Parse(String),\n}\n\n")
            f.write("pub struct KlionsConfig {\n")
            f.write("    pub home: String,\n}\n\n")
            f.write("impl KlionsConfig {\n")
            f.write("    pub fn load() -> Self {\n")
            f.write('        let home = std::env::var("KLIONS_HOME")\n')
            f.write('            .unwrap_or_else(|_| ".klions".to_string());\n')
            f.write("        Self { home }\n    }\n}\n\n")
            f.write("pub fn klions_banner() -> String {\n")
            f.write('    format!("KLIONS {}", KLIONS_VERSION)\n')
            f.write("}\n")

        with open(os.path.join(crate_dir, "tests.rs"), "w",
                  encoding="utf-8") as f:
            f.write("#[test]\nfn klions_chalta_hai() {\n")
            f.write('    assert!(klions_banner().starts_with("KLIONS"));\n')
            f.write("}\n\n#[test]\nfn ext_theek_hai() {\n")
            f.write('    assert_eq!(KLIONS_EXT, "klions");\n}\n')

    # उदाहरण की files
    os.makedirs(os.path.join(jad, "examples"))
    with open(os.path.join(jad, "examples", "xor.klions"), "w",
              encoding="utf-8") as f:
        f.write("// KLIONS में XOR\nmodel Xor {\n")
        f.write("    tensor<f32, [2]> input\n}\n")
    with open(os.path.join(jad, "examples", "mnist.kl"), "w",
              encoding="utf-8") as f:
        f.write("// KLIONS में MNIST\ntrain Net using mnist\n")

    # docs
    os.makedirs(os.path.join(jad, "docs"))
    with open(os.path.join(jad, "README.md"), "w", encoding="utf-8") as f:
        f.write("# KLIONS\n\nKLIONS एक AI-first systems भाषा है.\n\n")
        f.write("## चलाओ\n\n```\nklionsc build main.klions\n```\n\n")
        f.write("Binary: `klionsc`. Library: `libklions.so`.\n")
        f.write("Environment: `KLIONS_HOME`.\n")
    with open(os.path.join(jad, "docs", "syntax.md"), "w",
              encoding="utf-8") as f:
        f.write("# KLIONS का व्याकरण\n\nहर file `.klions` या `.kl` होती है.\n")

    # VS Code extension
    ext = os.path.join(jad, "editors", "vscode")
    os.makedirs(ext)
    with open(os.path.join(ext, "package.json"), "w", encoding="utf-8") as f:
        f.write('{\n  "name": "klions",\n')
        f.write('  "displayName": "KLIONS",\n')
        f.write('  "contributes": {\n    "languages": [{\n')
        f.write('      "id": "klions",\n')
        f.write('      "extensions": [".klions", ".kl"]\n    }]\n  }\n}\n')

    # बनी हुई चीज़ें — इन्हें छूना नहीं चाहिए
    os.makedirs(os.path.join(jad, "target", "debug"))
    with open(os.path.join(jad, "target", "debug", "libklions.so"), "wb") as f:
        f.write(b"\x7fELF nakli binary klions klions klions")

    return jad


if __name__ == "__main__":
    import tempfile
    p = banao(os.path.join(tempfile.mkdtemp(), "klions"))
    ginti = 0
    for root, dirs, files in os.walk(p):
        ginti += len(files)
    print("नक़ली workspace बना:", p)
    print("files:", ginti)
