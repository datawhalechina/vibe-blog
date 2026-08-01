"""Task-scoped logging and event dependency wiring."""

import json
import logging
import re


LOGGER_NAMES = (
    "services.blog_generator.generator",
    "services.blog_generator.agents.researcher",
    "services.blog_generator.agents.planner",
    "services.blog_generator.agents.writer",
    "services.blog_generator.agents.questioner",
    "services.blog_generator.agents.coder",
    "services.blog_generator.agents.artist",
    "services.blog_generator.agents.reviewer",
    "services.blog_generator.agents.assembler",
    "services.blog_generator.agents.search_coordinator",
    "services.blog_generator.services.search_service",
    "services.media.image_service",
)


class SSELogHandler(logging.Handler):
    """Forward generation logs and recognized search events to a task stream."""

    def __init__(self, task_manager, task_id):
        super().__init__()
        self.task_manager = task_manager
        self.task_id = task_id

    def emit(self, record):
        if self.task_manager and record.name.startswith("services.blog_generator"):
            if not self.task_manager.get_queue(self.task_id):
                logging.getLogger(record.name).removeHandler(self)
                return
            msg = self.format(record)
            self.task_manager.send_event(
                self.task_id,
                "log",
                {
                    "level": record.levelname,
                    "logger": record.name.split(".")[-1],
                    "message": msg,
                },
            )
            self._emit_structured_search_event(msg)

    def _emit_structured_search_event(self, msg):
        try:
            match = re.search(r"(?:Web Search 搜索|智能.*搜索)[：:]\s*(.+)", msg)
            if match:
                self.task_manager.send_event(
                    self.task_id,
                    "result",
                    {
                        "type": "search_started",
                        "data": {"query": match.group(1).strip()},
                    },
                )
                return
            if "请求参数" in msg and "search_query" in msg:
                payload_match = re.search(r"\{.*\}", msg)
                if payload_match:
                    try:
                        payload = json.loads(payload_match.group(0))
                        self.task_manager.send_event(
                            self.task_id,
                            "result",
                            {
                                "type": "search_started",
                                "data": {"query": payload.get("search_query", "")},
                            },
                        )
                    except json.JSONDecodeError:
                        pass
                return
            crawl_match = re.search(r"深度抓取完成[：:]\s*(\d+)", msg)
            if crawl_match:
                self.task_manager.send_event(
                    self.task_id,
                    "result",
                    {
                        "type": "crawl_completed",
                        "data": {"count": int(crawl_match.group(1))},
                    },
                )
                return
            if "智能搜索完成" in msg:
                self.task_manager.send_event(
                    self.task_id,
                    "result",
                    {"type": "search_completed", "data": {"message": msg}},
                )
        except Exception:
            pass


class TaskEventBridge:
    """Attach task logging and inject task-aware collaborators."""

    def __init__(self, generator, task_manager, task_id):
        self.generator = generator
        self.task_manager = task_manager
        self.task_id = task_id
        self.logger_names = LOGGER_NAMES
        self.handler = None

    def attach(self):
        if not self.task_manager or self.handler is not None:
            return self.handler
        self.handler = SSELogHandler(self.task_manager, self.task_id)
        self.handler.setLevel(logging.INFO)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        for logger_name in self.logger_names:
            logging.getLogger(logger_name).addHandler(self.handler)
        return self.handler

    def inject_dependencies(self):
        if not self.task_manager:
            return
        try:
            llm = self.generator.llm
            llm.task_manager = self.task_manager
            llm.task_id = self.task_id
            from utils.llm_logger import LLMCallLogger

            llm.llm_logger = LLMCallLogger(self.task_id)
        except Exception:
            pass
        try:
            researcher = self.generator.researcher
            researcher.task_manager = self.task_manager
            researcher.task_id = self.task_id
            if researcher.search_service:
                researcher.search_service.task_manager = self.task_manager
                researcher.search_service.task_id = self.task_id
        except Exception:
            pass
        try:
            writer = self.generator.writer
            writer.task_manager = self.task_manager
            writer.task_id = self.task_id
        except Exception:
            pass

    def close(self):
        if self.handler is None:
            return
        for logger_name in self.logger_names:
            logging.getLogger(logger_name).removeHandler(self.handler)
        self.handler = None
