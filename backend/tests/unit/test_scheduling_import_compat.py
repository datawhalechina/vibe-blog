import importlib


MODULE_ALIASES = (
    ("services.task_queue.backoff", "services.scheduling.backoff"),
    ("services.task_queue.cron_executor", "services.scheduling.cron_executor"),
    ("services.task_queue.cron_parser", "services.scheduling.cron_parser"),
    ("services.task_queue.cron_scheduler", "services.scheduling.cron_scheduler"),
    ("services.task_queue.cron_timer", "services.scheduling.cron_timer"),
    ("services.task_queue.manager", "services.scheduling.manager"),
    (
        "services.task_queue.migrate_to_cron_jobs",
        "repositories.tasks.migrate_to_cron_jobs",
    ),
    ("services.task_queue.pipeline", "services.scheduling.pipeline"),
    ("services.task_queue.scheduler", "services.scheduling.scheduler"),
    ("services.task_queue.db", "repositories.tasks.db"),
    ("services.task_queue.models", "models.scheduling"),
)


def test_scheduling_new_packages_are_importable():
    assert importlib.import_module("services.scheduling")
    assert importlib.import_module("repositories.tasks")
    assert importlib.import_module("models.scheduling")


def test_legacy_task_queue_modules_alias_new_modules():
    for legacy_name, current_name in MODULE_ALIASES:
        legacy = importlib.import_module(legacy_name)
        current = importlib.import_module(current_name)

        assert legacy is current, f"{legacy_name} does not alias {current_name}"


def test_public_scheduling_api_keeps_existing_types():
    legacy = importlib.import_module("services.task_queue")
    current = importlib.import_module("services.scheduling")

    assert legacy.TaskQueueManager is current.TaskQueueManager
    assert legacy.TaskDB is current.TaskDB
    assert legacy.BlogTask is current.BlogTask
    assert legacy.parse_schedule is current.parse_schedule
