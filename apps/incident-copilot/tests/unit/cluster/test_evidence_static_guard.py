"""Static guard for NFR5: `cluster/evidence.py` may never reference a
write/mutating Kubernetes API verb. This is the "assert at import-time
no write method is referenced" mechanism named in Components/Test Strategy
-- implemented as an AST scan (attribute-access nodes only, so the rule's
own docstring naming these verbs doesn't trip the guard) so it runs as a
normal CI unit test.
[Source: architecture/components.md, architecture/test-strategy-and-standards.md]
"""

import ast
from pathlib import Path

_FORBIDDEN_VERB_PREFIXES = ("patch_", "delete_", "create_", "replace_")


def test_evidence_module_references_no_write_verb() -> None:
    source = Path("src/incident_copilot/cluster/evidence.py").read_text()
    tree = ast.parse(source)

    found = sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr.startswith(_FORBIDDEN_VERB_PREFIXES)
        }
    )

    assert found == [], f"cluster/evidence.py references forbidden write verb(s): {found}"
