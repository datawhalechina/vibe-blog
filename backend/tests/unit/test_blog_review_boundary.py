import importlib


def test_blog_generation_facade_preserves_core_object_identity():
    facade = importlib.import_module("services.blog_generation")
    generator = importlib.import_module("services.blog_generator.generator")
    blog_service = importlib.import_module("services.blog_generator.blog_service")
    prompts = importlib.import_module("services.blog_generator.prompts")

    assert facade.BlogGenerator is generator.BlogGenerator
    assert facade.BlogService is blog_service.BlogService
    assert facade.get_blog_service is blog_service.get_blog_service
    assert facade.get_prompt_manager is prompts.get_prompt_manager


def test_review_facade_preserves_reviewer_and_guideline_identity():
    facade = importlib.import_module("services.review")
    reviewer = importlib.import_module("services.blog_generator.agents.reviewer")
    guidelines = importlib.import_module("services.blog_generator.review_guidelines")

    assert facade.ReviewerAgent is reviewer.ReviewerAgent
    assert facade.get_guidelines is guidelines.get_guidelines


def test_services_package_uses_blog_generation_facade():
    services = importlib.import_module("services")
    facade = importlib.import_module("services.blog_generation")

    assert services.BlogGenerator is facade.BlogGenerator
    assert services.BlogService is facade.BlogService
