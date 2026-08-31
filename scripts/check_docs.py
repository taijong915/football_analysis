"""문서 정합성 결정론적 검사.

`analysis-verifier` 서브에이전트가 1단계로 실행하는 스크립트이며, 사람이 직접
돌려도 된다. LLM 판단이 필요 없는 세 가지만 기계적으로 확인한다:

1. 엠대시("—")·엔대시("–") 사용 (문서에서 금지, `CLAUDE.md` 참고 사항)
2. 마크다운/HTML 문서의 이미지 상대경로가 실제 파일을 가리키는가
3. `CLAUDE.md` <-> `GEMINI.md`의 공통 섹션 본문 차이 (드리프트 후보, 의도된
   분기인지 판단은 사람/메인 세션 몫)

사용법:
    .venv\\Scripts\\python.exe scripts/check_docs.py

종료 코드: 1·2번에서 발견된 문제 수(0이면 통과). 3번은 정보성이라 종료 코드에
반영하지 않는다.
"""
import difflib
import os
import re
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.venv', '.git', '.ipynb_checkpoints', '__pycache__', 'node_modules'}


def walk_files(exts):
    """확장자가 exts에 속하는 파일 경로를 저장소 전체에서 순회한다."""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in exts:
                yield os.path.join(dirpath, fn)


def rel(path):
    return os.path.relpath(path, ROOT).replace('\\', '/')


# --- 1. 엠대시 / 엔대시 린트 ------------------------------------------------

# 그 문자를 "쓰지 말라"고 규정·인용하는 라인은 의도적 예외다. 실제 산문에서는
# "엠대시"라는 단어를 쓸 일이 없으므로, 이 토큰이 있으면 규칙/메타 라인으로 본다.
DASH_RULE_MARKERS = ('U+201', '엠대시', '엔대시', 'em dash', 'en dash', 'em-dash', 'en-dash')
DASH_RE = re.compile('[–—]')  # 엔대시(U+2013) / 엠대시(U+2014)


def check_dashes():
    hits = []
    for path in walk_files({'.md', '.ipynb', '.py'}):
        try:
            with open(path, encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            if DASH_RE.search(line) and not any(m in line for m in DASH_RULE_MARKERS):
                hits.append((rel(path), i, line.strip()[:160]))
    return hits


# --- 2. 이미지 링크 검사 --------------------------------------------------

MD_IMG_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
HTML_IMG_RE = re.compile(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
EXTERNAL_RE = re.compile(r'^(https?:|data:|//)', re.IGNORECASE)


def check_images():
    missing = []
    for path in walk_files({'.md', '.html'}):
        # `.claude/`의 에이전트 스펙 등은 예시로 `![](경로)` 문법을 본문에 쓰므로 제외
        if os.sep + '.claude' + os.sep in path:
            continue
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        refs = MD_IMG_RE.findall(text) + HTML_IMG_RE.findall(text)
        base = os.path.dirname(path)
        for ref in refs:
            # `![](path "제목")` 형태에서 경로만, 앵커/쿼리 제거
            src = ref.strip().split()[0].strip().split('#')[0].split('?')[0]
            if not src or EXTERNAL_RE.match(src):
                continue
            target = os.path.normpath(os.path.join(base, src))
            if not os.path.isfile(target):
                missing.append((rel(path), src))
    return missing


# --- 3. CLAUDE.md <-> GEMINI.md 공통 섹션 비교 ---------------------------

# 두 파일에서 본문이 (거의) 동일해야 하는 섹션의 정규화 제목 조각
SYNC_SECTIONS = ('분석워크플로우', '명령어', '아키텍처', '참고사항', '정기검토')

# CLI 이름 차이는 의도된 것이므로 비교 전에 지운다. 남는 차이만 드리프트 후보.
NAME_NORMALIZE = (
    ('CLAUDE.md', '<G>'), ('GEMINI.md', '<G>'), ('claude.md', '<g>'), ('gemini.md', '<g>'),
    ('Claude Code', '<CLI>'), ('Gemini / Antigravity CLI', '<CLI>'),
    ('Antigravity CLI', '<CLI>'), ('Gemini', '<CLI>'), ('Claude', '<CLI>'),
)


def normalize_names(line):
    for a, b in NAME_NORMALIZE:
        line = line.replace(a, b)
    return line


def parse_sections(path):
    """'## '로 시작하는 섹션을 {정규화 제목: 본문 라인 리스트}로 반환한다."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    sections, title, buf = {}, None, []
    for line in lines:
        if line.startswith('## '):
            if title is not None:
                sections[title] = buf
            raw = line[3:].strip()
            title = raw.replace('CLAUDE.md', '').replace('GEMINI.md', '').replace('및', '').replace(' ', '')
            buf = []
        else:
            buf.append(line)
    if title is not None:
        sections[title] = buf
    return sections


def check_doc_sync():
    claude = parse_sections(os.path.join(ROOT, 'CLAUDE.md'))
    gemini = parse_sections(os.path.join(ROOT, 'GEMINI.md'))
    out = []
    for frag in SYNC_SECTIONS:
        c_hit = [k for k in claude if frag in k]
        g_hit = [k for k in gemini if frag in k]
        if not c_hit or not g_hit:
            out.append((frag, f"한쪽에서 섹션을 못 찾음 (CLAUDE: {c_hit}, GEMINI: {g_hit})", []))
            continue
        c_body = [normalize_names(x) for x in claude[c_hit[0]]]
        g_body = [normalize_names(x) for x in gemini[g_hit[0]]]
        if c_body == g_body:
            continue
        ud = list(difflib.unified_diff(
            c_body, g_body,
            fromfile=f'CLAUDE.md :: {c_hit[0]}', tofile=f'GEMINI.md :: {g_hit[0]}',
            lineterm=''))
        out.append((frag, None, ud))
    return out


# --- 실행 ---------------------------------------------------------------

def main():
    dashes = check_dashes()
    missing = check_images()
    sync = check_doc_sync()

    print("=== 1. 엠대시/엔대시 린트 ===")
    if not dashes:
        print("문제 없음")
    else:
        for path, ln, text in dashes:
            print(f"  {path}:{ln}  {text}")

    print("\n=== 2. 이미지 링크 (상대경로 -> 실제 파일) ===")
    if not missing:
        print("문제 없음")
    else:
        for path, src in missing:
            print(f"  {path}  ->  {src}  (없음)")

    print("\n=== 3. CLAUDE.md <-> GEMINI.md 공통 섹션 차이 (정보성, 의도된 분기일 수 있음) ===")
    if not sync:
        print("공통 섹션 본문 동일")
    else:
        for frag, note, ud in sync:
            print(f"\n  [{frag}]")
            if note:
                print(f"    {note}")
            for line in ud:
                print(f"    {line}")

    fails = len(dashes) + len(missing)
    print(f"\n요약: 엠대시/엔대시 {len(dashes)}건, 누락 이미지 {len(missing)}건, "
          f"동기화 검토 대상 섹션 {len(sync)}개. (종료 코드 {fails})")
    return fails


if __name__ == '__main__':
    sys.exit(min(main(), 125))
