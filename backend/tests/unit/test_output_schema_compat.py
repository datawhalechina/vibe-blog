import pytest

from services.blog_generator import schemas
from services.blog_generator.schemas import outputs
from services.blog_generator.schemas import state


OUTPUT_MODEL_NAMES = (
    "SectionOutline",
    "BlogOutline",
    "SectionContent",
    "CodeBlock",
    "ImageResource",
    "VaguePoint",
    "QuestionResult",
    "ReviewIssue",
    "LearningObjective",
    "AudienceAnalysis",
    "VerbatimDataItem",
    "InstructionalAnalysis",
    "InformationArchitecture",
    "SearchResult",
    "KnowledgeGap",
    "SearchHistoryItem",
)

LEGACY_PACKAGE_EXPORTS = (
    "SectionOutline",
    "SectionContent",
    "CodeBlock",
    "ImageResource",
    "VaguePoint",
    "QuestionResult",
    "ReviewIssue",
    "BlogOutline",
    "KnowledgeGap",
    "SearchHistoryItem",
)


@pytest.mark.parametrize("model_name", OUTPUT_MODEL_NAMES)
def test_state_reexports_output_model_identity(model_name):
    assert getattr(state, model_name) is getattr(outputs, model_name)


@pytest.mark.parametrize("model_name", LEGACY_PACKAGE_EXPORTS)
def test_package_keeps_legacy_output_model_identity(model_name):
    assert getattr(schemas, model_name) is getattr(outputs, model_name)


def test_shared_state_remains_owned_by_state_module():
    assert schemas.SharedState is state.SharedState
    assert not hasattr(outputs, "SharedState")
