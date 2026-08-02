from collections import defaultdict
from threading import Lock

import pytest

from services.blog_generator.agents.writer import WriterAgent


def _state(*titles: str) -> dict:
    return {
        "outline": {
            "title": "Writer recovery",
            "sections": [
                {"title": title, "key_concept": title}
                for title in titles
            ],
        },
        "target_length": "mini",
    }


def test_failed_parallel_sections_recover_once_in_outline_order(monkeypatch):
    agent = WriterAgent(object())
    attempts = defaultdict(int)
    attempts_lock = Lock()

    def write_section(**kwargs):
        title = kwargs["section_outline"]["title"]
        with attempts_lock:
            attempts[title] += 1
            attempt = attempts[title]
        if attempt == 1:
            raise RuntimeError("concurrent stream disconnected")
        return {"title": title, "content": f"Recovered {title}"}

    monkeypatch.setattr(agent, "write_section", write_section)

    result = agent.run(_state("One", "Two", "Three"), max_workers=3)

    assert [section["title"] for section in result["sections"]] == [
        "One",
        "Two",
        "Three",
    ]
    assert dict(attempts) == {"One": 2, "Two": 2, "Three": 2}


def test_serial_recovery_does_not_rerun_parallel_successes(monkeypatch):
    agent = WriterAgent(object())
    attempts = defaultdict(int)
    attempts_lock = Lock()

    def write_section(**kwargs):
        title = kwargs["section_outline"]["title"]
        with attempts_lock:
            attempts[title] += 1
            attempt = attempts[title]
        if title == "Retry" and attempt == 1:
            raise RuntimeError("concurrent stream disconnected")
        return {"title": title, "content": f"Content {title}"}

    monkeypatch.setattr(agent, "write_section", write_section)

    result = agent.run(_state("Keep", "Retry"), max_workers=3)

    assert [section["title"] for section in result["sections"]] == [
        "Keep",
        "Retry",
    ]
    assert dict(attempts) == {"Keep": 1, "Retry": 2}


def test_serial_recovery_does_not_loop_after_a_second_failure(monkeypatch):
    agent = WriterAgent(object())
    attempts = defaultdict(int)
    attempts_lock = Lock()

    def write_section(**kwargs):
        title = kwargs["section_outline"]["title"]
        with attempts_lock:
            attempts[title] += 1
        if title == "Always fails":
            raise RuntimeError("provider unavailable")
        return {"title": title, "content": "Available"}

    monkeypatch.setattr(agent, "write_section", write_section)

    result = agent.run(_state("Always fails", "Available"), max_workers=3)

    assert [section["title"] for section in result["sections"]] == ["Available"]
    assert dict(attempts) == {"Always fails": 2, "Available": 1}


@pytest.mark.parametrize("empty_content", [None, "   "])
def test_empty_llm_content_triggers_serial_recovery(monkeypatch, empty_content):
    agent = WriterAgent(object())
    attempts = 0
    attempts_lock = Lock()

    def write_section(**kwargs):
        nonlocal attempts
        with attempts_lock:
            attempts += 1
            attempt = attempts
        content = empty_content if attempt == 1 else "Recovered content"
        return {
            "title": kwargs["section_outline"]["title"],
            "content": content,
        }

    monkeypatch.setattr(agent, "write_section", write_section)

    result = agent.run(_state("Retry empty response"), max_workers=3)

    assert result["sections"][0]["content"] == "Recovered content"
    assert attempts == 2
