from typing import Any, Dict, Generator
def txt2json(text: str) -> Generator:
    for i in text.splitlines():
        if not i.strip().startswith('#') and i.strip():
            ret = {k: ( v == 'TRUE' if v in ['TRUE', 'FALSE'] else v) for k, v in zip(('domain', 'domain_initial_dot', 'path', 'secure', 'expires', 'name', 'value'), i.split('\t'))}
            ret.pop('domain_initial_dot')
            yield ret

