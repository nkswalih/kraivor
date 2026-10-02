"""The indexing helpers must return a list on every path.

`index_entities` and `index_relationships` used to `return` (None) when
nothing was extracted and `return <list>` otherwise. The only caller,
`knowledge_indexer`, did `if entities:` which is falsy for both, so the
inconsistency stayed invisible - until anyone iterated the result, which
raised `TypeError` on exactly the items that happened to contain no
recognised technology names.

The empty path returns before opening a session, so these need no database.
"""

from typing import Any, cast

import pytest

from app.knowledge_engine.graph.knowledge_graph import (
    KnowledgeGraph,
    extract_entities,
    extract_relationships,
)

pytestmark = pytest.mark.unit

# Contains no entry from TECH_ENTITIES and no RELATIONSHIP_PATTERNS match.
BORING = "the meeting notes were short and unremarkable"


class TestEmptyPathsReturnAList:
    async def test_index_entities_returns_an_empty_list(self) -> None:
        result = await KnowledgeGraph().index_entities("ws-1", "item-1", BORING)
        assert result == []

    async def test_index_relationships_returns_an_empty_list(self) -> None:
        result = await KnowledgeGraph().index_relationships("ws-1", BORING)
        assert result == []

    @pytest.mark.parametrize(
        ("result", "label"),
        [
            pytest.param(extract_entities(BORING), "extract_entities", id="entities"),
            pytest.param(
                extract_relationships(BORING), "extract_relationships", id="rels"
            ),
        ],
    )
    def test_extraction_really_is_empty(self, result: list[dict], label: str) -> None:
        """Guards the premise: if this stops holding the two tests above are
        exercising the database path instead of the early return."""
        assert result == [], f"{label} unexpectedly matched something in {BORING!r}"

    @pytest.mark.parametrize("text", [BORING, ""])
    async def test_result_is_iterable_whatever_the_input(self, text: str) -> None:
        """The failure mode being fixed: iterating None raised TypeError."""
        for value in (
            await KnowledgeGraph().index_entities("ws-1", "item-1", text),
            await KnowledgeGraph().index_relationships("ws-1", text),
        ):
            assert isinstance(value, list)
            assert list(value) == []


class TestExtractionMatchesKnownContent:
    """Sanity check that the empty path is not trivially always taken."""

    def test_a_named_technology_is_extracted(self) -> None:
        found = extract_entities("We migrated the service to Postgres last year")
        names = [e["name"] for e in found]
        assert "postgres" in names

    def test_entities_carry_a_type(self) -> None:
        found = cast(list[dict[str, Any]], extract_entities("deployed on Kubernetes"))
        assert all("name" in e and "type" in e for e in found)

    def test_relationship_between_two_technologies(self) -> None:
        found = extract_relationships("React talks to the Postgres API")
        assert isinstance(found, list)
