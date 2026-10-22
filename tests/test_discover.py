from pathlib import Path
from tempfile import TemporaryDirectory
from exegesis.core import discover, unique_artifacts, slug_for


def test_comments_and_headings():
    sample = '''# Essays
[A](https://example.org/a.pdf)
<!-- [B](https://example.org/b.pdf) -->
<!--
[C](https://example.org/c.pdf)
-->
[D](https://example.org/a.pdf)
'''
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / 'README.md'
        path.write_text(sample)
        active = discover(path)
        assert [r['title'] for r in active] == ['A', 'D']
        assert len(unique_artifacts(active)) == 1
        all_links = discover(path, include_comments=True)
        assert [r['visibility'] for r in all_links] == ['active', 'commented', 'commented', 'active']
        assert all_links[0]['section'] == 'Essays'


def test_slug_is_stable_and_unique():
    assert slug_for('https://a.test/x.pdf') == slug_for('https://a.test/x.pdf')
    assert slug_for('https://a.test/x.pdf') != slug_for('https://b.test/x.pdf')
