"""Corpus discovery and acquisition. No network access during discovery."""
from __future__ import annotations
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LINK = re.compile(r'(?<!!)\[([^\]\n]+)\]\((https?://[^\s)]+(?:%20[^\s)]*)*)\)')
HEADING = re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*$')
COMMENT = re.compile(r'<!--|-->')


def is_pdf(url):
    return urlparse(url).path.lower().endswith('.pdf')


def discover(source: Path, include_comments=False):
    """Track HTML comments across lines; retain occurrences and their provenance."""
    lines = source.read_text(encoding='utf-8').splitlines()
    records, in_comment, section = [], False, 'Uncategorized'
    for lineno, line in enumerate(lines, 1):
        # Mask commented portions without disturbing offsets in the original line.
        active = list(line)
        comment_spans = []
        start = 0
        state = in_comment
        for token in COMMENT.finditer(line):
            if token.group() == '<!--' and not state:
                start, state = token.start(), True
            elif token.group() == '-->' and state:
                comment_spans.append((start, token.end()))
                state = False
            # Nested HTML comments are invalid and deliberately not supported.
        if state:
            comment_spans.append((start if not in_comment else 0, len(line)))
        # When a comment ends and another starts, track each span independently.
        for a, b in comment_spans:
            for i in range(a, b): active[i] = ' '
        visible = ''.join(active)
        match = HEADING.match(visible)
        if match:
            section = match.group(1).strip()
        for link in LINK.finditer(line):
            url = link.group(2)
            if not is_pdf(url):
                continue
            commented = any(a <= link.start() < b for a, b in comment_spans)
            if commented and not include_comments:
                continue
            records.append({
                'title': link.group(1).strip(), 'url': url,
                'source': str(source), 'line': lineno, 'section': section,
                'visibility': 'commented' if commented else 'active',
                'discovery_method': 'direct',
            })
        in_comment = state
    return records


def write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def unique_artifacts(records):
    grouped = {}
    for record in records:
        grouped.setdefault(record['url'], []).append(record)
    return grouped


def fetch(url: str, dest: Path, timeout=45, retries=2):
    """Atomic PDF download, basic content validation, and SHA-256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        temp = dest.with_suffix('.part')
        try:
            req = Request(url, headers={'User-Agent': 'exegesis/0.1 (+local research corpus)'})
            with urlopen(req, timeout=timeout) as response, temp.open('wb') as out:
                header = response.read(8192)
                if not header.lstrip().startswith(b'%PDF-'):
                    raise ValueError('Response does not begin with a PDF header')
                out.write(header)
                import shutil
                shutil.copyfileobj(response, out)
            data = temp.read_bytes()
            if b'%%EOF' not in data[-4096:]:
                raise ValueError('PDF EOF marker missing near file end')
            digest = hashlib.sha256(data).hexdigest()
            temp.replace(dest)
            return {'status': 'ok', 'sha256': digest, 'bytes': len(data), 'path': str(dest)}
        except (OSError, HTTPError, URLError, ValueError) as exc:
            temp.unlink(missing_ok=True)
            if attempt == retries:
                return {'status': 'error', 'error': str(exc)}
            time.sleep(min(2 ** attempt, 5))


def extract_pdf(pdf: Path, output: Path):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError('Install PDF support: pip install -e ".[pdf]"') from exc
    doc = fitz.open(pdf)
    if not doc.is_pdf:
        raise ValueError('Not a PDF document')
    pages = []
    for i, page in enumerate(doc):
        pages.append({'page': i + 1, 'text': page.get_text(sort=True)})
    payload = {'pdf': str(pdf), 'pages': pages, 'page_count': len(pages),
               'characters': sum(len(p['text']) for p in pages)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    doc.close()
    return payload


def slug_for(url):
    name = unquote(Path(urlparse(url).path).stem)
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:64] or 'document'
    return slug + '-' + hashlib.sha256(url.encode()).hexdigest()[:12]
