import argparse
import hashlib
import json
import sys
from pathlib import Path
from .core import discover, read_jsonl, write_jsonl, unique_artifacts, fetch, extract_pdf, slug_for


def main(argv=None):
    parser = argparse.ArgumentParser(prog='exegesis')
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('discover', help='Read PDF links from Markdown')
    d.add_argument('readme', type=Path)
    d.add_argument('--include-comments', action='store_true')
    f = sub.add_parser('fetch', help='Download discovered PDFs')
    f.add_argument('--dry-run', action='store_true')
    f.add_argument('--limit', type=int)
    e = sub.add_parser('extract', help='Extract page-aware text')
    e.add_argument('--limit', type=int)
    s = sub.add_parser('summarize', help='Run local Ollama summaries')
    s.add_argument('--model', default='granite4.1:3b')
    s.add_argument('--endpoint', default='http://127.0.0.1:11434')
    s.add_argument('--limit', type=int)
    sub.add_parser('report')
    args = parser.parse_args(argv)
    root = args.data_dir
    manifest = root / 'manifest.jsonl'
    if args.command == 'discover':
        records = discover(args.readme, args.include_comments)
        write_jsonl(manifest, records)
        print(f'{len(records)} PDF link occurrences, {len(unique_artifacts(records))} unique URLs; wrote {manifest}')
        return
    records = read_jsonl(manifest)
    if not records:
        parser.error(f'No manifest records at {manifest}; run discover first')
    grouped = unique_artifacts(records)
    if args.command == 'report':
        print(f'Link occurrences: {len(records)}; unique PDF URLs: {len(grouped)}')
        print(f'Active occurrences: {sum(r["visibility"] == "active" for r in records)}')
        print(f'Commented occurrences: {sum(r["visibility"] == "commented" for r in records)}')
        status = read_jsonl(root / 'fetch-status.jsonl')
        print('Downloaded:', sum(r.get('status') == 'ok' for r in status))
        print('Failed:', sum(r.get('status') == 'error' for r in status))
        return
    urls = list(grouped)
    if args.command == 'fetch':
        status_path = root / 'fetch-status.jsonl'
        old = {r['url']: r for r in read_jsonl(status_path)}
        pending = [(url, root / 'pdf' / (slug_for(url) + '.pdf')) for url in urls]
        pending = [(u, p) for u, p in pending if not (old.get(u, {}).get('status') == 'ok' and p.exists())]
        if args.limit is not None: pending = pending[:args.limit]
        for url, path in pending:
            if args.dry_run:
                print(f'WOULD FETCH {url} -> {path}')
                continue
            result = fetch(url, path)
            old[url] = {'url': url, **result}
            write_jsonl(status_path, old.values())
            print(f'{result["status"]}: {url}', flush=True)
        return
    status = {r['url']: r for r in read_jsonl(root / 'fetch-status.jsonl')}
    ready = [(url, Path(status[url]['path'])) for url in urls
             if status.get(url, {}).get('status') == 'ok' and Path(status[url]['path']).exists()]
    if args.command == 'extract':
        todo = [(u, p, root / 'extracted' / (slug_for(u) + '.json')) for u, p in ready]
        todo = [(u, p, o) for u, p, o in todo if not o.exists()]
        if args.limit is not None: todo = todo[:args.limit]
        for url, path, output in todo:
            try:
                result = extract_pdf(path, output)
                print(f'EXTRACTED {result["page_count"]} pages, {result["characters"]} chars: {url}', flush=True)
            except Exception as exc:
                print(f'ERROR {url}: {exc}', file=sys.stderr)
        return
    if args.command == 'summarize':
        from .ollama import summarize
        todo = []
        for url, path in ready:
            source = root / 'extracted' / (slug_for(url) + '.json')
            output = root / 'summaries' / args.model.replace(':', '-') / (slug_for(url) + '.json')
            if source.exists() and not output.exists(): todo.append((url, source, output))
        if args.limit is not None: todo = todo[:args.limit]
        for url, source, output in todo:
            try:
                payload = json.loads(source.read_text(encoding='utf-8'))
                result = summarize(payload, args.model, args.endpoint)
                result['url'] = url
                result['source_sha256'] = status[url]['sha256']
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'SUMMARIZED {url}', flush=True)
            except Exception as exc:
                print(f'ERROR {url}: {exc}', file=sys.stderr)

if __name__ == '__main__':
    main()
