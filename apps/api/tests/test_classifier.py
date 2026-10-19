from app.modules.email.classifier import classify_email
from app.modules.rag.retrieval import reciprocal_rank_fusion


def test_rejection():
    result = classify_email(
        subject="Update",
        text_body="Unfortunately we will not be moving forward with your application",
    )
    assert result.classification == "REJECTION"


def test_interview():
    result = classify_email(
        subject="Pohovor",
        text_body="Rádi bychom Vás pozvali na pohovor přes Zoom",
    )
    assert result.classification in {"INTERVIEW_INVITE", "INTERVIEW_INVITATION"}


def test_rrf():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert fused[0][0] in {"a", "b"}
