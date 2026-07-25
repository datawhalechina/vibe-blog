import importlib


MODULE_ALIASES = (
    ("services.file_parser_service", "services.documents.file_parser_service"),
    ("services.knowledge_service", "services.documents.knowledge_service"),
    ("services.book_scanner_service", "services.documents.book_scanner_service"),
    ("services.oss_service", "services.publishing.oss_service"),
    ("services.xhs_service", "services.publishing.xhs_service"),
    ("services.publishers", "services.publishing.publishers"),
    (
        "services.publishers.publisher",
        "services.publishing.publishers.publisher",
    ),
    (
        "services.publishers.workflow_engine",
        "services.publishing.publishers.workflow_engine",
    ),
)


def test_documents_and_publishing_packages_are_importable():
    assert importlib.import_module("services.documents")
    assert importlib.import_module("services.publishing")


def test_legacy_modules_alias_new_modules():
    for legacy_name, current_name in MODULE_ALIASES:
        legacy = importlib.import_module(legacy_name)
        current = importlib.import_module(current_name)

        assert legacy is current, f"{legacy_name} does not alias {current_name}"


def test_file_parser_templates_still_resolve_after_move():
    parser = importlib.import_module("services.documents.file_parser_service")

    assert parser._templates_dir.is_dir()


def test_package_apis_expose_existing_services():
    documents = importlib.import_module("services.documents")
    publishing = importlib.import_module("services.publishing")

    assert documents.get_file_parser
    assert documents.get_knowledge_service
    assert publishing.get_oss_service
    assert publishing.get_xhs_service
