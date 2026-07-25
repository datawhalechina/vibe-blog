import importlib


def test_llm_service_old_and_new_modules_share_identity():
    legacy = importlib.import_module("services.llm_service")
    current = importlib.import_module("services.llm.service")

    assert legacy is current
    assert legacy.LLMService is current.LLMService
    assert legacy.get_llm_service is current.get_llm_service
    assert legacy._strip_thinking is current._strip_thinking
    assert legacy._rate_limit is current._rate_limit


def test_llm_factory_old_and_new_modules_share_identity():
    legacy = importlib.import_module("services.llm_factory")
    current = importlib.import_module("services.llm.factory")

    assert legacy is current
    assert legacy.create_llm_client is current.create_llm_client
    assert legacy.PROVIDER_CONFIGS is current.PROVIDER_CONFIGS


def test_llm_package_exposes_public_api():
    package = importlib.import_module("services.llm")
    service = importlib.import_module("services.llm.service")
    factory = importlib.import_module("services.llm.factory")

    assert package.LLMService is service.LLMService
    assert package.get_llm_service is service.get_llm_service
    assert package.init_llm_service is service.init_llm_service
    assert package.create_llm_client is factory.create_llm_client
