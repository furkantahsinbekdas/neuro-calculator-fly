# -*- coding: utf-8 -*-
"""rename_docs_en.py — docs/en/ dosya adlarini Ingilizce standarda cevirir (idempotent).

Kullanim (projenin ana dizininde):
    python rename_docs_en.py            # kuru calisma (hicbir sey degismez)
    python rename_docs_en.py --apply    # yeniden adlandir + referanslari guncelle

Kurallar:
    RAPOR_FAZ_X.en.md / RAPOR_FAZ_X.md  -> PHASE_X_REPORT.md
    RAPOR_ARAYUZ.en.md                  -> UI_REPORT.md
    PROJE_KAPANIS.en.md                 -> PROJECT_CLOSING.md
    RAPOR_HESAP_MAKINESI*.en.md         -> CALCULATOR_REPORT.md
    RAPOR_IKI_HANELI.en.md              -> TWO_DIGIT_REPORT.md
    V1_OZET.en.md                       -> V1_SUMMARY.md
    PHASES.en.md                        -> PHASES.md

Hedef dosya zaten varsa UZERINE YAZMAZ (atlar). Ad degisince docs/en/*.md, README.md ve
numcog/*.md icindeki ESKI ad referanslari da yeni ada guncellenir.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs", "en")

RULES = [
    (re.compile(r"^RAPOR_FAZ_(.+)\.en\.md$"), r"PHASE_\1_REPORT.md"),
    (re.compile(r"^RAPOR_FAZ_(.+)\.md$"), r"PHASE_\1_REPORT.md"),
    (re.compile(r"^RAPOR_ARAYUZ\.en\.md$"), "UI_REPORT.md"),
    (re.compile(r"^PROJE_KAPANIS\.en\.md$"), "PROJECT_CLOSING.md"),
    (re.compile(r"^RAPOR_HESAP_MAKINESI[A-Z_]*\.en\.md$"), "CALCULATOR_REPORT.md"),
    (re.compile(r"^RAPOR_IKI_HANELI\.en\.md$"), "TWO_DIGIT_REPORT.md"),
    (re.compile(r"^V1_OZET\.en\.md$"), "V1_SUMMARY.md"),
    (re.compile(r"^PHASES\.en\.md$"), "PHASES.md"),
]

REF_GLOBS = [DOCS, ROOT]


def new_name(old):
    for pat, rep in RULES:
        if pat.match(old):
            return pat.sub(rep, old)
    return None


def ref_files():
    files = []
    for d in os.listdir(DOCS):
        if d.lower().endswith(".md"):
            files.append(os.path.join(DOCS, d))
    rp = os.path.join(ROOT, "README.md")
    if os.path.isfile(rp):
        files.append(rp)
    numcog = os.path.join(ROOT, "numcog")
    if os.path.isdir(numcog):
        for f in os.listdir(numcog):
            if f.lower().endswith(".md"):
                files.append(os.path.join(numcog, f))
    return files


def main():
    apply = "--apply" in sys.argv[1:]
    print("rename_docs_en.py — %s" % ("UYGULA" if apply else "KURU ÇALIŞMA (--apply ile yazar)"))
    print("-" * 78)
    renames, skipped = [], []
    for f in sorted(os.listdir(DOCS)):
        if not f.lower().endswith(".md"):
            continue
        new = new_name(f)
        if not new or new == f:
            continue
        src, dst = os.path.join(DOCS, f), os.path.join(DOCS, new)
        if os.path.exists(dst):
            skipped.append((f, new, "hedef zaten var"))
            continue
        renames.append((f, new))
    if not renames:
        print("yeniden adlandirilacak dosya yok.")
    for old, new in renames:
        print("  %-38s -> %s" % (old, new))
        if apply:
            os.rename(os.path.join(DOCS, old), os.path.join(DOCS, new))
    for old, new, why in skipped:
        print("  ATLANDI %-30s -> %-28s (%s)" % (old, new, why))

    touched = 0
    if apply and renames:
        print("-" * 78)
        for path in ref_files():
            try:
                text = io.open(path, encoding="utf-8").read()
            except Exception:                                        # noqa: BLE001
                continue
            new_text = text
            for old, new in renames:
                if old in new_text:
                    new_text = new_text.replace(old, new)
            if new_text != text:
                io.open(path, "w", encoding="utf-8", newline="").write(new_text)
                touched += 1
                print("  referans güncellendi: %s" % os.path.relpath(path, ROOT))
    print("-" * 78)
    print("yeniden adlandirildi: %d | atlandi: %d | referans dosyasi: %d"
          % (len(renames) if apply else 0, len(skipped), touched))
    if not apply:
        print("(kuru çalışma: hiçbir dosya değişmedi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
