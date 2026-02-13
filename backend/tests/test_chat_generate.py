"""
一键生成 API + generate_service 测试
测试用例 GN1-GN8: 端到端一键生成流程（Mock Agent 层）
"""


class TestGenerateEndpoint:
    def _create_session(self, chat_client):
        resp = chat_client.post('/api/chat/session', json={"topic": "AI 入门"})
        return resp.get_json()["session_id"]

    def test_gn1_generate_returns_task_id(self, chat_client):
        """GN1: 一键生成 → 返回 task_id + 202"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/generate', json={})
        assert resp.status_code == 202
        data = resp.get_json()
        assert "task_id" in data
        assert data["session_id"] == sid

    def test_gn2_generate_nonexistent_session(self, chat_client):
        """GN2: 不存在的会话 → 404"""
        resp = chat_client.post('/api/chat/session/ws_bad/generate', json={})
        assert resp.status_code == 404

    def test_gn3_generate_creates_task(self, chat_client):
        """GN3: 一键生成 → 返回的 task_id 格式正确"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/generate', json={})
        task_id = resp.get_json()["task_id"]
        assert task_id.startswith("task_")
        assert len(task_id) > 5


class TestGenerateService:
    def test_gn4_full_pipeline(self, chat_app):
        """GN4: generate_service 完整流程 — search → outline → write → review → factcheck → humanize → assemble"""
        from services.chat.generate_service import run_chat_generate
        from services.task_service import TaskManager

        session_mgr = chat_app.chat_session_mgr
        dispatcher = chat_app.mock_dispatcher
        task_manager = TaskManager.__new__(TaskManager)
        task_manager._initialized = False
        task_manager.__init__()
        task_id = task_manager.create_task()

        # 创建会话
        session = session_mgr.create(topic="测试一键生成")
        sid = session.session_id

        # 运行（同步等待线程完成）
        with chat_app.app_context():
            thread = run_chat_generate(
                session_id=sid,
                session_mgr=session_mgr,
                dispatcher=dispatcher,
                task_manager=task_manager,
                task_id=task_id,
                app=chat_app,
            )
            thread.join(timeout=10)

        # 验证 dispatcher 方法被调用
        dispatcher.search.assert_called_once()
        dispatcher.generate_outline.assert_called_once()
        dispatcher.write_section.assert_called()
        dispatcher.review.assert_called_once()
        dispatcher.factcheck.assert_called_once()
        dispatcher.humanize.assert_called_once()
        dispatcher.assemble.assert_called_once()

        # 验证任务完成
        task = task_manager.get_task(task_id)
        assert task.status == "completed"

    def test_gn5_session_status_updated(self, chat_app):
        """GN5: 一键生成完成后 session status 变为 completed"""
        from services.chat.generate_service import run_chat_generate
        from services.task_service import TaskManager

        session_mgr = chat_app.chat_session_mgr
        dispatcher = chat_app.mock_dispatcher
        task_manager = TaskManager.__new__(TaskManager)
        task_manager._initialized = False
        task_manager.__init__()
        task_id = task_manager.create_task()

        session = session_mgr.create(topic="状态测试")
        sid = session.session_id

        with chat_app.app_context():
            thread = run_chat_generate(
                session_id=sid,
                session_mgr=session_mgr,
                dispatcher=dispatcher,
                task_manager=task_manager,
                task_id=task_id,
                app=chat_app,
            )
            thread.join(timeout=10)

        final_session = session_mgr.get(sid)
        assert final_session.status == "completed"

    def test_gn6_nonexistent_session_error(self, chat_app):
        """GN6: 不存在的 session → task 状态为 failed"""
        from services.chat.generate_service import run_chat_generate
        from services.task_service import TaskManager

        session_mgr = chat_app.chat_session_mgr
        dispatcher = chat_app.mock_dispatcher
        task_manager = TaskManager.__new__(TaskManager)
        task_manager._initialized = False
        task_manager.__init__()
        task_id = task_manager.create_task()

        with chat_app.app_context():
            thread = run_chat_generate(
                session_id="ws_nonexistent",
                session_mgr=session_mgr,
                dispatcher=dispatcher,
                task_manager=task_manager,
                task_id=task_id,
                app=chat_app,
            )
            thread.join(timeout=10)

        task = task_manager.get_task(task_id)
        assert task.status == "failed"

    def test_gn7_sse_events_emitted(self, chat_app):
        """GN7: 一键生成过程中 SSE 事件被正确发送"""
        from services.chat.generate_service import run_chat_generate
        from services.task_service import TaskManager

        session_mgr = chat_app.chat_session_mgr
        dispatcher = chat_app.mock_dispatcher
        task_manager = TaskManager.__new__(TaskManager)
        task_manager._initialized = False
        task_manager.__init__()
        task_id = task_manager.create_task()

        session = session_mgr.create(topic="SSE 测试")
        sid = session.session_id

        with chat_app.app_context():
            thread = run_chat_generate(
                session_id=sid,
                session_mgr=session_mgr,
                dispatcher=dispatcher,
                task_manager=task_manager,
                task_id=task_id,
                app=chat_app,
            )
            thread.join(timeout=10)

        # 收集队列中的所有事件
        queue = task_manager.get_queue(task_id)
        events = []
        while queue and not queue.empty():
            events.append(queue.get_nowait())

        event_types = [e['event'] for e in events]
        # 应该有 progress 和 result 和 complete 事件
        assert 'progress' in event_types
        assert 'result' in event_types
        assert 'complete' in event_types

    def test_gn8_outline_failure_stops_pipeline(self, chat_app):
        """GN8: 大纲生成失败 → pipeline 中止，task 状态为 failed"""
        from services.chat.generate_service import run_chat_generate
        from services.task_service import TaskManager

        session_mgr = chat_app.chat_session_mgr
        dispatcher = chat_app.mock_dispatcher
        # 让 generate_outline 返回空
        dispatcher.generate_outline.return_value = {"outline": None}

        task_manager = TaskManager.__new__(TaskManager)
        task_manager._initialized = False
        task_manager.__init__()
        task_id = task_manager.create_task()

        session = session_mgr.create(topic="大纲失败测试")
        sid = session.session_id

        with chat_app.app_context():
            thread = run_chat_generate(
                session_id=sid,
                session_mgr=session_mgr,
                dispatcher=dispatcher,
                task_manager=task_manager,
                task_id=task_id,
                app=chat_app,
            )
            thread.join(timeout=10)

        task = task_manager.get_task(task_id)
        assert task.status == "failed"
        # write 不应该被调用
        dispatcher.write_section.assert_not_called()
