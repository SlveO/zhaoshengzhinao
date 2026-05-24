from types import SimpleNamespace

from knowledge.indexer import _build_document_text, _sanitize_meta_val


def test_campus_life_document_text_includes_qa_and_sources():
    data = SimpleNamespace(
        title="华南师范大学 收费与住宿",
        data_type="campus_life",
        year=2025,
        province="广东",
        extra_meta={},
        content={
            "category": "收费与住宿",
            "topic": "2025年学费与住宿费",
            "summary": "住宿费800—1600元/生·学年。",
            "text": "文科类6060元，理工外语体育类6850元。",
            "keywords": ["学费", "住宿费"],
            "qa": [{"question": "住宿费多少？", "answer": "800—1600元/生·学年。"}],
            "source_title": "招生章程",
            "source_url": "https://zsb.scnu.edu.cn/a/20250515/684.html",
        },
    )

    text = _build_document_text(data)

    assert "收费与住宿" in text
    assert "问:住宿费多少？" in text
    assert "800—1600元" in text
    assert "https://zsb.scnu.edu.cn/a/20250515/684.html" in text


def test_sanitize_meta_serializes_lists_and_dicts():
    assert _sanitize_meta_val(None) == ""
    assert _sanitize_meta_val(["学费", "住宿费"]) == '["学费", "住宿费"]'
    assert _sanitize_meta_val({"category": "招生"}) == '{"category": "招生"}'
