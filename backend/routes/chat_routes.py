"""
对话式写作 REST API 路由
15+ 个端点，覆盖会话管理、调研、大纲、写作、质量检查、组装全流程。
"""
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

_session_mgr = None
_dispatcher = None


def init_chat_service(session_mgr, dispatcher):
    global _session_mgr, _dispatcher
    _session_mgr = session_mgr
    _dispatcher = dispatcher


def _get_session_or_404(session_id):
    session = _session_mgr.get(session_id)
    if not session:
        return None, jsonify({"error": "Session not found"}), 404
    return session, None, None


# ========== 会话管理 ==========

@chat_bp.route('/session', methods=['POST'])
def create_session():
    data = request.get_json(silent=True) or {}
    topic = data.get('topic', '').strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    kwargs = {k: v for k, v in data.items()
              if k in ('article_type', 'target_audience', 'target_length')}
    session = _session_mgr.create(topic=topic, **kwargs)
    return jsonify({"session_id": session.session_id, "topic": session.topic,
                     "status": session.status}), 201


@chat_bp.route('/sessions', methods=['GET'])
def list_sessions():
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    sessions = _session_mgr.list(limit=limit, offset=offset)
    return jsonify([{"session_id": s.session_id, "topic": s.topic,
                      "status": s.status} for s in sessions])


@chat_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    from dataclasses import asdict
    return jsonify(asdict(session))


# ========== 调研 ==========

@chat_bp.route('/session/<session_id>/search', methods=['POST'])
def do_search(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.search(session, **{k: v for k, v in data.items() if k == 'max_results'})
    _session_mgr.update(session_id, search_results=result.get("search_results", []),
                        status="researching")
    return jsonify(result)


@chat_bp.route('/session/<session_id>/knowledge-gaps', methods=['POST'])
def knowledge_gaps(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.detect_knowledge_gaps(session, content=data.get("content", ""))
    return jsonify(result)


# ========== 大纲 ==========

@chat_bp.route('/session/<session_id>/outline', methods=['POST'])
def generate_outline(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    result = _dispatcher.generate_outline(session)
    outline = result.get("outline")
    if outline:
        sections = [{"id": s.get("id"), "title": s.get("title"), "content": ""}
                     for s in outline.get("sections", [])]
        _session_mgr.update(session_id, outline=outline, sections=sections, status="outlining")
    return jsonify(result)


@chat_bp.route('/session/<session_id>/outline/edit', methods=['POST'])
def edit_outline(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.edit_outline(session, changes=data)
    outline = result.get("outline")
    if outline:
        _session_mgr.update(session_id, outline=outline)
    return jsonify(result)


# ========== 写作 ==========

@chat_bp.route('/session/<session_id>/write', methods=['POST'])
def write_section(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    section_id = data.get("section_id", "")
    if not section_id:
        return jsonify({"error": "section_id is required"}), 400
    result = _dispatcher.write_section(session, section_id)
    if "error" in result:
        return jsonify(result), 400
    # 更新 sections 列表
    section_data = result.get("section", {})
    sections = list(session.sections or [])
    updated = False
    for i, s in enumerate(sections):
        if s.get("id") == section_id:
            sections[i] = section_data
            updated = True
            break
    if not updated:
        sections.append(section_data)
    _session_mgr.update(session_id, sections=sections, status="writing")
    return jsonify(result)


@chat_bp.route('/session/<session_id>/edit', methods=['POST'])
def edit_section(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.edit_section(session, data.get("section_id", ""),
                                       data.get("instructions", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@chat_bp.route('/session/<session_id>/enhance', methods=['POST'])
def enhance_section(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.enhance_section(session, data.get("section_id", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ========== 代码 & 配图 ==========

@chat_bp.route('/session/<session_id>/code', methods=['POST'])
def generate_code(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.generate_code(session, data.get("description", ""),
                                        data.get("language", "python"))
    return jsonify(result)


@chat_bp.route('/session/<session_id>/image', methods=['POST'])
def generate_image(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.generate_image(session, data.get("description", ""),
                                         data.get("image_type", "diagram"))
    return jsonify(result)


# ========== 质量检查 ==========

@chat_bp.route('/session/<session_id>/review', methods=['POST'])
def review(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    result = _dispatcher.review(session)
    _session_mgr.update(session_id, status="reviewing")
    return jsonify(result)


@chat_bp.route('/session/<session_id>/factcheck', methods=['POST'])
def factcheck(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    result = _dispatcher.factcheck(session)
    return jsonify(result)


@chat_bp.route('/session/<session_id>/humanize', methods=['POST'])
def humanize(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    data = request.get_json(silent=True) or {}
    result = _dispatcher.humanize(session, section_id=data.get("section_id"))
    return jsonify(result)


# ========== 组装 & 发布 ==========

@chat_bp.route('/session/<session_id>/assemble', methods=['POST'])
def assemble(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    result = _dispatcher.assemble(session)
    _session_mgr.update(session_id, status="assembling")
    return jsonify(result)


@chat_bp.route('/session/<session_id>/publish', methods=['POST'])
def publish(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    _session_mgr.update(session_id, status="completed")
    return jsonify({"status": "completed", "session_id": session_id})


@chat_bp.route('/session/<session_id>/preview', methods=['GET'])
def preview(session_id):
    session, err, code = _get_session_or_404(session_id)
    if err:
        return err, code
    result = _dispatcher.get_preview(session)
    return jsonify(result)
