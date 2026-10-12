# -*- coding: utf-8 -*-
"""self_test for storyboard-consistency-check — v2 template, four defenses:
1) SystemExit/Exception capture  2) Unicode-safe matching
3) fixtures written with newline=""  4) last line: SUMMARY: PASS n/n
NOTE: this tool is text-only by contract; no test touches image files.
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard_check as mod  # noqa: E402

main = mod.main


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = main(argv) or 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


FIX = tempfile.mkdtemp(prefix="scc_selftest_")


def wfile(name, content):
    path = os.path.join(FIX, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return path


BASE_REG = "[entities]\nalice: type=character, aliases=ali\nbob: type=character\nkey: type=prop\ncastle: type=scene\n\n---\n\n"


def scene(n, chars="alice, bob", props="key", loc="castle", notes="ali holds the key"):
    parts = ["## S%d" % n]
    if chars is not None:
        parts.append("Characters: " + chars)
    if props is not None:
        parts.append("Props: " + props)
    if loc is not None:
        parts.append("Scene: " + loc)
    if notes is not None:
        parts.append("Notes: " + notes)
    return "\n".join(parts)


def rules(text):
    return [f["rule"] for f in mod.check_text(text)["findings"]]


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# ---------- [A] functional ----------
@case("consistent script passes clean")
def t01():
    text = BASE_REG + scene(1) + "\n\n" + scene(2, notes="ali and bob talk")
    r = mod.check_text(text)
    assert r["findings"] == [], r


@case("scene count and entity count reported")
def t02():
    r = mod.check_text(BASE_REG + scene(1))
    assert r["scenes"] == 1 and r["entities"] == 4, r


@case("unknown-entity fires for unregistered name")
def t03():
    text = BASE_REG + scene(1, chars="alice, zorro")
    assert "unknown-entity" in rules(text)


@case("unknown prop fires")
def t04():
    text = BASE_REG + scene(1, props="key, lightsaber")
    assert "unknown-entity" in rules(text)


@case("unknown scene fires")
def t05():
    text = BASE_REG + scene(1, loc="spaceship")
    assert "unknown-entity" in rules(text)


@case("alias resolves to canonical entity")
def t06():
    text = BASE_REG + scene(1, chars="ali")
    r = mod.check_text(text)
    errs = [f for f in r["findings"] if f["severity"] == "error"]
    assert errs == [], r


@case("alias-collision fires")
def t07():
    text = "[entities]\nalice: type=character, aliases=sam\nsam2: type=character, aliases=sam\n\n---\n\n## S1\nCharacters: alice\n"
    assert "alias-collision" in rules(text)


@case("type-mismatch: prop under Characters")
def t08():
    text = BASE_REG + scene(1, chars="key")
    assert "type-mismatch" in rules(text)


@case("type-mismatch: character under Props")
def t09():
    text = BASE_REG + scene(1, props="bob")
    assert "type-mismatch" in rules(text)


@case("duplicate-scene fires")
def t10():
    text = BASE_REG + scene(1) + "\n\n" + scene(1)
    assert "duplicate-scene" in rules(text)


@case("scene-order warning on decreasing numbers")
def t11():
    text = BASE_REG + scene(2) + "\n\n" + scene(1)
    r = rules(text)
    assert "scene-order" in r and "duplicate-scene" not in r, r


@case("empty-scene fires")
def t12():
    text = BASE_REG + "## S1\n\n## S2\nNotes: ali alone\n"
    assert "empty-scene" in rules(text)


@case("undeclared-use: alias in notes not listed")
def t13():
    text = BASE_REG + scene(1, chars="bob", notes="ali arrives late")
    assert "undeclared-use" in rules(text)


@case("listed entity mentioned in notes is fine")
def t14():
    text = BASE_REG + scene(1, notes="ali holds the key")
    assert "undeclared-use" not in rules(text)


@case("continuity-gap fires for S1,S2-absent,S3")
def t15():
    text = (BASE_REG + scene(1) + "\n\n"
            + scene(2, chars="bob", props="", loc="castle", notes="bob waits")
            + "\n\n" + scene(3))
    r = rules(text)
    assert "continuity-gap" in r, r


@case("no gap when entity present every scene")
def t16():
    text = BASE_REG + scene(1) + "\n\n" + scene(2) + "\n\n" + scene(3)
    assert "continuity-gap" not in rules(text)


@case("unused-entity warning")
def t17():
    text = "[entities]\nalice: type=character\nghost: type=character\n\n---\n\n## S1\nCharacters: alice\n"
    assert "unused-entity" in rules(text)


@case("registry heading is not a scene")
def t18():
    r = mod.check_text(BASE_REG + scene(1))
    assert r["scenes"] == 1, r


@case("case-insensitive entity listing")
def t19():
    text = BASE_REG + scene(1, chars="Alice, BOB")
    r = mod.check_text(text)
    assert r["findings"] == [], r


@case("json output shape and exit codes")
def t20():
    path = wfile("bad.txt", BASE_REG + scene(1, chars="nobody"))
    code, out, _ = run_cli([path, "--json"])
    data = json.loads(out)
    assert code == 1 and data["scenes"] == 1
    assert "unknown-entity" in [f["rule"] for f in data["findings"]]


@case("clean file exits 0")
def t21():
    path = wfile("ok.txt", BASE_REG + scene(1))
    code, out, _ = run_cli([path])
    assert code == 0 and "0 error(s)" in out, out


@case("error file exits 1")
def t22():
    path = wfile("err.txt", BASE_REG + scene(1, chars="ghost"))
    code, _, _ = run_cli([path])
    assert code == 1


@case("warning-only exits 0")
def t23():
    path = wfile("warn.txt",
                 "[entities]\nalice: type=character\nghost: type=character\n\n---\n\n## S1\nCharacters: alice\n")
    code, _, _ = run_cli([path])
    assert code == 0


@case("stdin mode works")
def t24():
    buf = io.StringIO(BASE_REG + scene(1))
    old = sys.stdin
    sys.stdin = buf
    try:
        code, out, _ = run_cli(["-"])
    finally:
        sys.stdin = old
    assert code == 0 and "1 scenes" in out, out


@case("Scene label without S prefix still numbered")
def t25():
    text = BASE_REG + "## Scene 7\nCharacters: alice\n"
    r = mod.check_text(text)
    assert r["scenes"] == 1 and not any(
        f["rule"] in ("unknown-entity", "empty-scene") for f in r["findings"]), r


@case("Chinese separator in lists accepted")
def t26():
    text = "[entities]\n张三: type=character\n李四: type=character\n\n---\n\n## S1\nCharacters: 张三，李四\nNotes: 张三和李四见面\n"
    r = mod.check_text(text)
    assert r["findings"] == [], r


@case("findings sorted by line")
def t27():
    text = BASE_REG + scene(2, chars="ghost2") + "\n\n" + scene(1, chars="ghost3")
    lines = [f["line"] for f in mod.check_text(text)["findings"]]
    assert lines == sorted(lines)


# ---------- [B] error paths ----------
@case("missing file exits 2")
def t28():
    code, _, err = run_cli([os.path.join(FIX, "nope.txt")])
    assert code == 2 and "cannot read" in err, err


@case("missing file --json prints json error")
def t29():
    code, out, _ = run_cli([os.path.join(FIX, "nope.txt"), "--json"])
    assert code == 2 and "error" in json.loads(out)


@case("directory as input exits 2")
def t30():
    assert run_cli([FIX])[0] == 2


@case("no arguments raises SystemExit 2")
def t31():
    try:
        main([])
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert e.code == 2


@case("--help exits 0")
def t32():
    code, out, _ = run_cli(["--help"])
    assert code == 0 and "usage" in out.lower()


@case("--version exits 0")
def t33():
    code, out, _ = run_cli(["--version"])
    assert code == 0 and "0.1.1" in out


@case("unknown flag exits 2")
def t34():
    assert run_cli(["--bogus"])[0] == 2


@case("findings always have four keys")
def t35():
    for f in mod.check_text(BASE_REG + scene(1, chars="ghost"))["findings"]:
        assert set(f) == {"rule", "severity", "line", "message"}


@case("no registry at all: every listing unknown")
def t36():
    r = rules("## S1\nCharacters: alice\n")
    assert r.count("unknown-entity") == 1 and "empty-scene" not in r, r


@case("no registry no scenes: zero findings is ok-ish")
def t37():
    r = mod.check_text("just some prose\n")
    assert r["scenes"] == 0 and r["findings"] == [], r


@case("check_text never raises on malformed input")
def t38():
    for s in ("", "[entities]\n", "## S1\n", "[entities]\nnocolon\n", "---\n"):
        mod.check_text(s)


@case("entity line with empty aliases tolerated")
def t39():
    text = "[entities]\nalice: type=character, aliases=\n\n---\n\n## S1\nCharacters: alice\n"
    assert mod.check_text(text)["findings"] == []


@case("unknown type field defaults to character")
def t40():
    text = "[entities]\nrock: type=mineral\n\n---\n\n## S1\nCharacters: rock\n"
    r = mod.check_text(text)
    assert not any(f["rule"] == "unknown-entity" for f in r["findings"]), r


# ---------- [C] extreme edge ----------
@case("empty string input")
def t41():
    r = mod.check_text("")
    assert r["scenes"] == 0 and r["findings"] == []


@case("whitespace-only input")
def t42():
    assert mod.check_text(" \n\t\n")["findings"] == []


@case("CRLF line endings")
def t43():
    text = (BASE_REG + scene(1)).replace("\n", "\r\n")
    assert mod.check_text(text)["findings"] == []


@case("unicode entity names")
def t44():
    text = "[entities]\n小明: type=character\n\n---\n\n## S1\nCharacters: 小明\nNotes: 小明出门\n"
    assert mod.check_text(text)["findings"] == []


@case("unicode notes with undeclared use")
def t45():
    text = "[entities]\n小明: type=character\n小红: type=character\n\n---\n\n## S1\nCharacters: 小明\nNotes: 小明等小红\n"
    assert "undeclared-use" in rules(text)


@case("very long notes line (100k chars)")
def t46():
    text = BASE_REG + scene(1, notes="ali " + "x" * 100000)
    r = mod.check_text(text)
    assert r["findings"] == [], r


@case("2000 scenes performance path")
def t47():
    text = BASE_REG + "\n\n".join(scene(i) for i in range(1, 2001))
    r = mod.check_text(text)
    assert r["scenes"] == 2000 and r["findings"] == [], r["findings"][:3]


@case("50 characters in one scene")
def t48():
    reg = "[entities]\n" + "".join("c%d: type=character\n" % i for i in range(50))
    text = reg + "---\n\n## S1\nCharacters: " + ", ".join("c%d" % i for i in range(50))
    assert mod.check_text(text)["findings"] == []


@case("alias equal to another entity name collides")
def t49():
    text = "[entities]\nalice: type=character\nbob: type=character\n\n---\n\n## S1\nCharacters: alice\n"
    text2 = "[entities]\nalice: type=character, aliases=bob\nbob: type=character\n\n---\n\n## S1\nCharacters: alice\n"
    assert "alias-collision" in rules(text2)
    assert "alias-collision" not in rules(text)


@case("punctuation around mentions in notes")
def t50():
    text = BASE_REG + scene(1, chars="bob", props="key", loc="castle",
                            notes="(ali?) yes, ALI! ...ali.")
    r = mod.check_text(text)
    assert any(f["rule"] == "undeclared-use" for f in r["findings"]), r


@case("BOM prefix tolerated")
def t51():
    text = ("\ufeff" + BASE_REG + scene(1)).replace("\ufeff[", "[")
    text = "\ufeff" + BASE_REG + scene(1)
    r = mod.check_text(text)
    assert r["findings"] == [], r


@case("scene with only Notes tracked")
def t52():
    text = BASE_REG + "## S1\nNotes: ali alone\n"
    r = mod.check_text(text)
    assert "empty-scene" not in [f["rule"] for f in r["findings"]], r


@case("heading inside notes text does not split scene")
def t53():
    text = BASE_REG + "## S1\nCharacters: alice\nNotes: sees ## S2 written on a sign\n"
    r = mod.check_text(text)
    assert r["scenes"] == 1, r


@case("gap detection across many scenes: only first reported")
def t54():
    text = (BASE_REG + scene(1) + "\n\n"
            + scene(2, chars="bob", props="key", loc="castle", notes="bob waits")
            + "\n\n" + scene(3) + "\n\n"
            + scene(4, chars="bob", props="key", loc="castle", notes="bob"))
    gaps = [f for f in mod.check_text(text)["findings"]
            if f["rule"] == "continuity-gap"]
    assert len(gaps) == 1, gaps


@case("entity name that is substring does not match")
def t55():
    text = "[entities]\nal: type=character\n\n---\n\n## S1\nCharacters: al\nNotes: the alley is dark\n"
    r = mod.check_text(text)
    assert not any(f["rule"] == "undeclared-use" for f in r["findings"]), r


@case("repeated runs deterministic")
def t56():
    text = BASE_REG + scene(1, chars="ghost") + "\n\n" + scene(2)
    assert mod.check_text(text) == mod.check_text(text)


@case("markdown ### headings accepted")
def t57():
    text = BASE_REG + "### S1\nCharacters: alice\n"
    assert mod.check_text(text)["scenes"] == 1


@case("scene lists with trailing commas tolerated")
def t58():
    text = BASE_REG + scene(1, chars="alice, bob,")
    assert mod.check_text(text)["findings"] == []


@case("entity listed twice in same scene")
def t59():
    text = BASE_REG + "## S1\nCharacters: alice, alice\n"
    r = mod.check_text(text)
    errs = [f for f in r["findings"] if f["severity"] == "error"]
    assert errs == [], r


@case("image-file mention in notes stays text-only")
def t60():
    text = BASE_REG + scene(1, notes="ali sketches frame_04.png; no file is read")
    r = mod.check_text(text)
    assert all("png" not in f["message"] or f["rule"] != "unknown-entity"
               for f in r["findings"])


@case("full CLI pipeline contract")
def t61():
    path = wfile("c61.txt", BASE_REG + scene(1, chars="ghost") + "\n\n" + scene(2))
    code, out, _ = run_cli([path])
    assert code == 1 and "unknown-entity" in out and "2 scenes" in out, out


@case("summary line format stable")
def t62():
    path = wfile("c62.txt", BASE_REG + scene(1))
    code, out, _ = run_cli([path])
    assert out.strip().endswith("checked 1 scenes, 4 entities: 0 error(s), 0 warning(s)"), out


@case("empty Props line tolerated")
def t63():
    text = BASE_REG + scene(1, props="")
    r = mod.check_text(text)
    errs = [f for f in r["findings"] if f["severity"] == "error"]
    assert errs == [], r


@case("three dashes alone between scenes")
def t64():
    text = BASE_REG + scene(1) + "\n\n---\n\n" + scene(2)
    assert mod.check_text(text)["findings"] == []


@case("emoji in notes")
def t65():
    text = BASE_REG + scene(1, notes="ali 🎉 finds the key")
    assert mod.check_text(text)["findings"] == []


class ToolTests(unittest.TestCase):
    pass


def _name(i, n):
    return "test_%03d_%s" % (i, re.sub(r"\W+", "_", n))


for _i, (_n, _fn) in enumerate(CASES):
    setattr(ToolTests, _name(_i, _n), lambda self, _f=_fn: _f())


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    for t, _ in r.failures + r.errors:
        print("FAIL:", t.id().split(".")[-1])
    print("SUMMARY: PASS %d/%d" % (total - fails, total))
    sys.exit(0 if fails == 0 else 1)
