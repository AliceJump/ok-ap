"""Validate i18n catalogs: check all locales compile and have no empty msgstr.

Usage:
    python scripts/validate_all.py
"""
import sys

try:
    import polib
except ImportError:
    print("polib not installed; run `uv sync --group dev` first")
    sys.exit(1)

LOCALES = ["zh_CN", "zh_TW", "en_US", "es_ES", "ja_JP", "ko_KR"]

failed = False
for lang in LOCALES:
    path = f"i18n/{lang}/LC_MESSAGES/ok.po"
    try:
        po = polib.pofile(path)
    except Exception as e:
        print(f"  ❌ {lang}: cannot load {path}: {e}")
        failed = True
        continue
    empty = [e for e in po if not e.msgstr and e.msgid]
    # 编译验证 .mo
    try:
        po.save_as_mofile(path.replace(".po", ".mo"))
        mo_ok = True
    except Exception as e:
        mo_ok = False
        print(f"  ❌ {lang}: .mo compile failed: {e}")
        failed = True
    print(f"  {'✅' if not empty and mo_ok else '❌'} {lang}: {len(po)} entries, {len(empty)} empty, mo={'ok' if mo_ok else 'fail'}")

if failed:
    sys.exit(1)
print("All locales OK")