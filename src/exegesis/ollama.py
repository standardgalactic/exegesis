"""Page-grounded hierarchical summaries through local Ollama HTTP API."""
import json
from urllib.request import Request, urlopen

SYSTEM = ('You are a careful scholarly analyst. Use only the supplied source text. '
          'Separate claims, evidence, assumptions and unresolved questions. '
          'Never invent page citations, equations, references, or conclusions. '
          'If text is incomplete, disclose the limitation.')


def generate(model, prompt, endpoint='http://127.0.0.1:11434', temperature=0):
    body = json.dumps({'model': model, 'stream': False,
                       'messages': [{'role': 'system', 'content': SYSTEM},
                                    {'role': 'user', 'content': prompt}],
                       'options': {'temperature': temperature}}).encode()
    req = Request(endpoint.rstrip('/') + '/api/chat', data=body,
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=900) as response:
        return json.load(response)['message']['content']


def chunk_pages(pages, max_chars=12000):
    chunks, current, length = [], [], 0
    for page in pages:
        text = page['text']
        # Split unusually long pages rather than dropping any source text.
        fragments = [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or ['']
        for part in fragments:
            entry = f"[Page {page['page']}]\n{part}"
            if current and length + len(entry) > max_chars:
                chunks.append('\n\n'.join(current))
                current, length = [], 0
            current.append(entry)
            length += len(entry)
    if current:
        chunks.append('\n\n'.join(current))
    return chunks


def summarize(payload, model, endpoint, max_chars=12000):
    chunks = chunk_pages(payload['pages'], max_chars)
    notes = []
    for i, chunk in enumerate(chunks, 1):
        prompt = (f'Analyze excerpt {i} of {len(chunks)} from a scholarly PDF. '
                  'Produce a concise account of its theses, arguments, definitions, '
                  'formal claims, and open questions. Cite only page labels explicitly '
                  'present in the excerpt. Do not infer missing text.\n\n' + chunk)
        notes.append(generate(model, prompt, endpoint))
    # Hierarchical aggregation avoids sending all extracted pages at once.
    current = notes
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 4):
            group = current[i:i + 4]
            next_level.append(generate(model,
                'Synthesize these excerpt analyses faithfully, preserving disagreements, '
                'uncertainties, and page citations. Do not introduce new claims.\n\n' +
                '\n\n'.join(group), endpoint))
        current = next_level
    final = generate(model,
        'Create a scholarly summary with headings: Central thesis; Argument and method; '
        'Definitions and mathematics; Evidence and limitations; Open questions. '
        'Distinguish proven results from proposals. Source is the following extracted '
        'analytical notes; citations must be grounded in those notes.\n\n' +
        (current[0] if current else 'No extractable text.'), endpoint)
    return {'model': model, 'chunk_count': len(chunks), 'notes': notes, 'summary': final,
            'warning': 'Model-generated interpretations require source verification.'}
