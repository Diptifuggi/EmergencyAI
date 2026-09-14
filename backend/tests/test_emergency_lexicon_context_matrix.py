from __future__ import annotations

import pytest

from app.services.emergency_lexicon import LEXICON, lexicon_matches
from app.services.incident_rules import extract_incident_facts, services_for_facts


# One natural English sentence per domain is exercised in five semantic
# contexts.  The lexicon should retain high-recall evidence, while the rule
# engine must gate dispatch using sentence context.
_DOMAIN_SENTENCES = {
    domain: resource.english[0]
    for domain, resource in LEXICON.items()
}
_CONTEXTS = (
    ("current", "There is {term} right now and please send help.", True),
    ("historical", "Yesterday there was {term}, but the report is from then.", False),
    ("hypothetical", "What should I do if there is {term}?", False),
    ("resolved", "There was {term}, but everything is fine now.", False),
    ("example", "This is a training example about {term}.", False),
)


@pytest.mark.parametrize(
    ("domain", "term", "context", "template", "current"),
    [
        (domain, term, context, template, current)
        for domain, term in _DOMAIN_SENTENCES.items()
        for context, template, current in _CONTEXTS
    ],
)
def test_domain_context_matrix(
    domain: str, term: str, context: str, template: str, current: bool
) -> None:
    text = template.format(term=term)
    assert domain in lexicon_matches(text, "en")
    facts = extract_incident_facts(text, "en")
    assert facts.current_emergency is current, (domain, context, text, facts)
    if not current:
        assert services_for_facts(facts) == []
