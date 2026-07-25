import importlib


ROUTE_MODULES = (
    "blog_routes",
    "book_routes",
    "chat_routes",
    "feishu_routes",
    "history_routes",
    "publish_routes",
    "queue_routes",
    "scheduler_routes",
    "settings_routes",
    "static_routes",
    "task_routes",
    "transform_routes",
    "xhs_routes",
)


def test_app_factory_is_exposed_from_api_package():
    package = importlib.import_module("api")
    factory = importlib.import_module("api.app_factory")

    assert package.create_app is factory.create_app


def test_new_api_boundaries_are_importable():
    assert importlib.import_module("api.schemas")
    assert importlib.import_module("api.errors")
    assert importlib.import_module("api.routes")


def test_legacy_route_modules_alias_api_route_modules():
    for module_name in ROUTE_MODULES:
        legacy = importlib.import_module(f"routes.{module_name}")
        current = importlib.import_module(f"api.routes.{module_name}")

        assert legacy is current, f"routes.{module_name} is not a module alias"


def test_legacy_route_registry_uses_new_registry():
    legacy = importlib.import_module("routes")
    current = importlib.import_module("api.routes")

    assert legacy.register_all_blueprints is current.register_all_blueprints
