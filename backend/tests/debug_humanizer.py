"""
复现 humanizer JSON 解析失败问题
验证 qwen3.5-plus 对 response_format={"type": "json_object"} 的支持情况
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from services.llm_service import init_llm_service
from config import get_config
from infrastructure.prompts import get_prompt_manager

cfg = get_config()
llm = init_llm_service({
    'AI_PROVIDER_FORMAT': cfg.AI_PROVIDER_FORMAT,
    'OPENAI_API_KEY': cfg.OPENAI_API_KEY,
    'OPENAI_API_BASE': cfg.OPENAI_API_BASE,
    'TEXT_MODEL': cfg.TEXT_MODEL,
})

SAMPLE_SECTION = """
### 为什么需要装饰器？

在日常开发中，我们经常会遇到这样的场景：多个函数需要执行相同的前置或后置操作。
此外，随着项目规模的不断演变，代码的可维护性变得至关重要。装饰器提供了一种优雅的解决方案，
它允许我们在不修改原函数代码的情况下，为函数添加额外的功能。值得注意的是，
这种模式在 Python 生态中被广泛采用，从 Flask 的路由装饰器到 pytest 的 fixture，
都是装饰器模式的深刻体现。
"""

pm = get_prompt_manager()

# ---- Test 1: Score (轻量调用) ----
print("=" * 60)
print("Test 1: humanizer_score (评分)")
print("=" * 60)
score_prompt = pm.render_humanizer_score(section_content=SAMPLE_SECTION)
print(f"Prompt 长度: {len(score_prompt)} 字符")

t0 = time.time()
score_resp = llm.chat(
    messages=[{"role": "user", "content": score_prompt}],
    response_format={"type": "json_object"},
    caller="debug-humanizer-score",
)
elapsed = time.time() - t0
print(f"耗时: {elapsed:.1f}s")
print(f"Response type: {type(score_resp)}")
print(f"Response repr: {repr(score_resp[:500]) if score_resp else repr(score_resp)}")

if score_resp and score_resp.strip():
    try:
        parsed = json.loads(score_resp)
        print(f"JSON 解析成功: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
else:
    print("!!! Response 为空 !!!")

# ---- Test 2: Rewrite (重量调用，这是失败的那个) ----
print("\n" + "=" * 60)
print("Test 2: humanizer rewrite (改写) — 这是生产环境失败的调用")
print("=" * 60)
rewrite_prompt = pm.render_humanizer(
    section_content=SAMPLE_SECTION,
    audience_adaptation="technical-beginner",
)
print(f"Prompt 长度: {len(rewrite_prompt)} 字符")

t0 = time.time()
rewrite_resp = llm.chat(
    messages=[{"role": "user", "content": rewrite_prompt}],
    response_format={"type": "json_object"},
    caller="debug-humanizer-rewrite",
)
elapsed = time.time() - t0
print(f"耗时: {elapsed:.1f}s")
print(f"Response type: {type(rewrite_resp)}")
print(f"Response repr: {repr(rewrite_resp[:500]) if rewrite_resp else repr(rewrite_resp)}")

if rewrite_resp and rewrite_resp.strip():
    try:
        parsed = json.loads(rewrite_resp)
        print(f"JSON 解析成功，humanized_content 长度: {len(parsed.get('humanized_content', ''))}")
        print(f"changes: {parsed.get('changes', [])}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        # 尝试提取
        from services.blog_generator.agents.humanizer import _extract_json
        try:
            parsed = _extract_json(rewrite_resp)
            print(f"_extract_json 成功: keys={list(parsed.keys())}")
        except Exception as e2:
            print(f"_extract_json 也失败: {e2}")
else:
    print("!!! Response 为空 !!!")

# ---- Test 3: 不带 response_format 对比 ----
print("\n" + "=" * 60)
print("Test 3: 不带 response_format 的改写调用（对比）")
print("=" * 60)

t0 = time.time()
raw_resp = llm.chat(
    messages=[{"role": "user", "content": rewrite_prompt}],
    caller="debug-humanizer-no-format",
)
elapsed = time.time() - t0
print(f"耗时: {elapsed:.1f}s")
print(f"Response type: {type(raw_resp)}")
print(f"Response 前 500 字符:\n{raw_resp[:500] if raw_resp else '(empty)'}")

if raw_resp and raw_resp.strip():
    try:
        parsed = json.loads(raw_resp)
        print(f"\n直接 json.loads 成功!")
    except json.JSONDecodeError:
        from services.blog_generator.agents.humanizer import _extract_json
        try:
            parsed = _extract_json(raw_resp)
            print(f"\n_extract_json 成功: keys={list(parsed.keys())}")
        except Exception as e:
            print(f"\n_extract_json 失败: {e}")

print("\n" + "=" * 60)
print("Done")
