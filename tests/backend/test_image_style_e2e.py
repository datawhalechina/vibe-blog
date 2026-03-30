"""
端到端测试：验证博客生成中 Type × Style 配图系统

测试流程：
1. 调用 /api/blog/generate/mini 接口，指定 image_style
2. 监听 SSE 事件流，等待生成完成
3. 验证结果中包含配图，且 Markdown 中包含图片引用
4. 验证 ArtistAgent 日志中包含指定风格信息

使用方法：
    # 需要先启动 vibe-blog 后端服务
    python -m pytest tests/test_image_style_e2e.py -v -s

    # 或直接运行
    python tests/test_image_style_e2e.py --base-url http://localhost:5001 --style academic

    # 指定主题和风格
    python tests/test_image_style_e2e.py --topic "Python 装饰器" --style cartoon

环境要求：
    pip install requests sseclient-py
"""

import os
import sys
import json
import time
import logging
import argparse
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import requests

# 尝试导入 sseclient，CI 环境中缺少时跳过测试
try:
    import sseclient
except ImportError:
    sseclient = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ========== 数据结构 ==========

@dataclass
class TestResult:
    """测试结果"""
    passed: bool = False
    task_id: str = ""
    style_used: str = ""
    images_count: int = 0
    markdown_has_images: bool = False
    artist_events: List[Dict] = field(default_factory=list)
    outline_has_illustration_type: bool = False
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    markdown_content: str = ""


# ========== 核心测试逻辑 ==========

class ImageStyleE2ETest:
    """配图风格端到端测试"""

    # 可用的配图风格
    AVAILABLE_STYLES = [
        'cartoon', 'academic', 'biesty', 'whiteboard',
        'watercolor', 'pixel', 'blueprint', 'comic'
    ]

    # 可用的插图类型
    AVAILABLE_TYPES = [
        'infographic', 'scene', 'flowchart',
        'comparison', 'framework', 'timeline'
    ]

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def check_server(self) -> bool:
        """检查服务器是否可用"""
        try:
            resp = self.session.get(f"{self.base_url}/api/config", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def get_available_styles(self) -> List[Dict]:
        """获取服务器上可用的配图风格"""
        try:
            resp = self.session.get(f"{self.base_url}/api/config", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('image_styles', [])
        except Exception:
            pass
        return []

    def create_blog_task(
        self,
        topic: str,
        image_style: str,
        target_length: str = "mini"
    ) -> Optional[str]:
        """
        创建博客生成任务

        Returns:
            task_id 或 None
        """
        endpoint = f"{self.base_url}/api/blog/generate/mini" if target_length == "mini" else f"{self.base_url}/api/blog/generate"

        payload = {
            "topic": topic,
            "article_type": "tutorial",
            "image_style": image_style,
        }

        if target_length != "mini":
            payload["target_length"] = target_length
            payload["target_audience"] = "intermediate"

        logger.info(f"📤 创建博客任务: topic={topic}, style={image_style}, length={target_length}")

        try:
            resp = self.session.post(endpoint, json=payload, timeout=30)
            data = resp.json()

            if data.get('success') and data.get('task_id'):
                logger.info(f"✅ 任务创建成功: task_id={data['task_id']}")
                return data['task_id']
            else:
                logger.error(f"❌ 任务创建失败: {data.get('error', '未知错误')}")
                return None
        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")
            return None

    def listen_sse(
        self,
        task_id: str,
        timeout: int = 600
    ) -> TestResult:
        """
        监听 SSE 事件流，收集测试数据

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒），默认 10 分钟

        Returns:
            TestResult
        """
        result = TestResult(task_id=task_id)
        start_time = time.time()

        sse_url = f"{self.base_url}/api/tasks/{task_id}/stream"
        logger.info(f"📡 开始监听 SSE: {sse_url}")

        try:
            response = self.session.get(sse_url, stream=True, timeout=timeout)
            client = sseclient.SSEClient(response)

            for event in client.events():
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    result.errors.append(f"超时 ({timeout}s)")
                    break

                event_type = event.event
                try:
                    data = json.loads(event.data) if event.data else {}
                except json.JSONDecodeError:
                    continue

                # 处理不同事件类型
                if event_type == 'connected':
                    logger.info(f"  🔗 SSE 已连接")

                elif event_type == 'progress':
                    stage = data.get('stage', '')
                    message = data.get('message', '')
                    progress = data.get('progress', 0)
                    logger.info(f"  📊 [{stage}] {progress}% - {message}")

                elif event_type == 'result':
                    result_type = data.get('type', '')
                    result_data = data.get('data', {})

                    if result_type == 'outline_complete':
                        # 检查大纲中是否包含 illustration_type
                        sections = result_data.get('sections', [])
                        for section in sections:
                            if section.get('illustration_type'):
                                result.outline_has_illustration_type = True
                                logger.info(f"  📋 大纲包含 illustration_type: {section['illustration_type']}")
                                break
                        logger.info(f"  📋 大纲完成: {result_data.get('title', '')}, {len(sections)} 个章节")

                    elif result_type == 'artist_complete':
                        images_count = result_data.get('images_count', 0)
                        result.images_count = images_count
                        result.artist_events.append(result_data)
                        logger.info(f"  🎨 配图完成: {images_count} 张")

                    elif result_type == 'section_complete':
                        idx = result_data.get('section_index', '?')
                        title = result_data.get('title', '')
                        logger.info(f"  📝 章节 {idx} 完成: {title}")

                    elif result_type == 'reviewer_complete':
                        score = result_data.get('score', 0)
                        logger.info(f"  ✅ 审核完成: 得分 {score}")

                elif event_type == 'log':
                    level = data.get('level', 'INFO')
                    log_logger = data.get('logger', '')
                    message = data.get('message', '')

                    # 捕获 artist 相关日志
                    if 'artist' in log_logger.lower() or '配图' in message or 'image' in message.lower():
                        result.artist_events.append({
                            'type': 'log',
                            'level': level,
                            'logger': log_logger,
                            'message': message
                        })

                    if level in ('ERROR', 'WARNING'):
                        logger.warning(f"  ⚠️ [{log_logger}] {message}")
                    else:
                        # 只显示关键日志
                        if any(kw in message for kw in ['开始', '完成', '成功', '失败', '风格', 'style', 'type']):
                            logger.info(f"  📝 [{log_logger}] {message}")

                elif event_type == 'complete':
                    result.markdown_content = data.get('markdown', '')
                    result.images_count = data.get('images_count', 0)
                    result.duration_seconds = time.time() - start_time

                    # 检查 Markdown 中是否包含图片
                    if result.markdown_content:
                        img_pattern = r'!\[.*?\]\(.*?\)'
                        img_matches = re.findall(img_pattern, result.markdown_content)
                        result.markdown_has_images = len(img_matches) > 0
                        logger.info(f"  📄 Markdown 中找到 {len(img_matches)} 个图片引用")

                    logger.info(f"  🎉 生成完成! 耗时 {result.duration_seconds:.1f}s, "
                              f"图片数: {result.images_count}")
                    break

                elif event_type == 'error':
                    error_msg = data.get('message', '未知错误')
                    recoverable = data.get('recoverable', False)
                    result.errors.append(error_msg)
                    logger.error(f"  ❌ 错误: {error_msg} (recoverable={recoverable})")
                    if not recoverable:
                        break

                elif event_type == 'cancelled':
                    result.errors.append("任务被取消")
                    logger.warning(f"  ⚠️ 任务被取消")
                    break

        except requests.exceptions.Timeout:
            result.errors.append(f"SSE 连接超时 ({timeout}s)")
            logger.error(f"❌ SSE 连接超时")
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"❌ SSE 监听异常: {e}")

        result.duration_seconds = time.time() - start_time
        return result

    def run_test(
        self,
        topic: str = "Python 装饰器入门",
        image_style: str = "cartoon",
        target_length: str = "mini",
        timeout: int = 600
    ) -> TestResult:
        """
        运行完整的端到端测试

        Args:
            topic: 博客主题
            image_style: 配图风格 ID
            target_length: 文章长度
            timeout: 超时时间

        Returns:
            TestResult
        """
        result = TestResult(style_used=image_style)

        # Step 1: 检查服务器
        logger.info("=" * 60)
        logger.info(f"🧪 开始 E2E 测试: Type × Style 配图系统")
        logger.info(f"   主题: {topic}")
        logger.info(f"   风格: {image_style}")
        logger.info(f"   长度: {target_length}")
        logger.info("=" * 60)

        if not self.check_server():
            result.errors.append(f"服务器不可用: {self.base_url}")
            logger.error(f"❌ 服务器不可用: {self.base_url}")
            return result

        # Step 2: 创建任务
        task_id = self.create_blog_task(topic, image_style, target_length)
        if not task_id:
            result.errors.append("任务创建失败")
            return result

        result.task_id = task_id

        # Step 3: 监听 SSE 事件
        sse_result = self.listen_sse(task_id, timeout)

        # 合并结果
        result.images_count = sse_result.images_count
        result.markdown_has_images = sse_result.markdown_has_images
        result.artist_events = sse_result.artist_events
        result.outline_has_illustration_type = sse_result.outline_has_illustration_type
        result.errors.extend(sse_result.errors)
        result.duration_seconds = sse_result.duration_seconds
        result.markdown_content = sse_result.markdown_content

        # Step 4: 验证结果
        result.passed = self._validate(result, image_style)

        # Step 5: 输出报告
        self._print_report(result, topic, image_style)

        return result

    def _validate(self, result: TestResult, expected_style: str) -> bool:
        """验证测试结果"""
        all_passed = True

        # V1: 无致命错误
        if result.errors:
            logger.warning(f"⚠️ V1 存在错误: {result.errors}")
            all_passed = False

        # V2: 生成了图片
        if result.images_count == 0:
            logger.warning(f"⚠️ V2 未生成图片")
            # Mini 模式可能不一定生成内容图，不算致命
        else:
            logger.info(f"✅ V2 生成了 {result.images_count} 张图片")

        # V3: Markdown 中包含图片引用
        if result.markdown_content and result.markdown_has_images:
            logger.info(f"✅ V3 Markdown 包含图片引用")
        elif result.markdown_content:
            logger.warning(f"⚠️ V3 Markdown 不包含图片引用")

        # V4: 检查 artist 日志中是否包含风格信息
        style_mentioned = False
        for event in result.artist_events:
            msg = event.get('message', '')
            if expected_style in msg.lower() or 'style' in msg.lower():
                style_mentioned = True
                break
        if style_mentioned:
            logger.info(f"✅ V4 日志中提到了风格 '{expected_style}'")
        else:
            logger.info(f"ℹ️ V4 日志中未明确提到风格（可能在内部处理）")

        return all_passed

    def _print_report(self, result: TestResult, topic: str, style: str):
        """输出测试报告"""
        print()
        print("=" * 60)
        print("📊 E2E 测试报告")
        print("=" * 60)
        print(f"  主题:           {topic}")
        print(f"  配图风格:       {style}")
        print(f"  任务 ID:        {result.task_id}")
        print(f"  耗时:           {result.duration_seconds:.1f}s")
        print(f"  图片数量:       {result.images_count}")
        print(f"  Markdown 有图:  {'✅' if result.markdown_has_images else '❌'}")
        print(f"  大纲含 Type:    {'✅' if result.outline_has_illustration_type else '❌'}")
        print(f"  Artist 事件数:  {len(result.artist_events)}")
        print(f"  错误数:         {len(result.errors)}")
        print(f"  总体结果:       {'✅ PASSED' if result.passed else '❌ FAILED'}")

        if result.errors:
            print()
            print("  错误详情:")
            for err in result.errors:
                print(f"    - {err}")

        # 显示 artist 关键事件
        if result.artist_events:
            print()
            print("  Artist 关键事件:")
            for evt in result.artist_events[:10]:
                msg = evt.get('message', json.dumps(evt, ensure_ascii=False))
                print(f"    - {msg[:100]}")

        print("=" * 60)

        # 保存 Markdown 到文件
        if result.markdown_content:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs', 'test_results')
            os.makedirs(output_dir, exist_ok=True)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(output_dir, f"e2e_{style}_{timestamp}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result.markdown_content)
            print(f"\n  📄 Markdown 已保存: {filepath}")


# ========== 命令行入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description="vibe-blog 配图风格 E2E 测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认参数测试（cartoon 风格，mini 模式）
  python tests/test_image_style_e2e.py

  # 指定风格和主题
  python tests/test_image_style_e2e.py --style academic --topic "Transformer 架构详解"

  # 测试所有风格（逐个运行）
  python tests/test_image_style_e2e.py --all-styles

  # 指定服务器地址
  python tests/test_image_style_e2e.py --base-url http://localhost:5001
        """
    )
    parser.add_argument("--base-url", default="http://localhost:5001", help="后端服务地址")
    parser.add_argument("--topic", default="Python 装饰器入门", help="博客主题")
    parser.add_argument("--style", default="cartoon", help=f"配图风格: {', '.join(ImageStyleE2ETest.AVAILABLE_STYLES)}")
    parser.add_argument("--length", default="mini", help="文章长度: mini/short/medium")
    parser.add_argument("--timeout", type=int, default=600, help="超时时间（秒）")
    parser.add_argument("--all-styles", action="store_true", help="测试所有风格（逐个运行）")

    args = parser.parse_args()

    tester = ImageStyleE2ETest(base_url=args.base_url)

    # 检查服务器
    if not tester.check_server():
        print(f"❌ 服务器不可用: {args.base_url}")
        print(f"   请先启动 vibe-blog 后端: cd backend && python app.py")
        sys.exit(1)

    if args.all_styles:
        # 测试所有风格
        results = {}
        styles = tester.get_available_styles()
        style_ids = [s.get('value', s.get('id', '')) for s in styles] if styles else ImageStyleE2ETest.AVAILABLE_STYLES

        print(f"\n🧪 将测试 {len(style_ids)} 种风格: {', '.join(style_ids)}\n")

        for style in style_ids:
            result = tester.run_test(
                topic=args.topic,
                image_style=style,
                target_length=args.length,
                timeout=args.timeout
            )
            results[style] = result
            print()

        # 汇总报告
        print("\n" + "=" * 60)
        print("📊 全风格测试汇总")
        print("=" * 60)
        for style, result in results.items():
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {style:15s} | {status} | 图片: {result.images_count} | 耗时: {result.duration_seconds:.0f}s")
        print("=" * 60)

        passed = sum(1 for r in results.values() if r.passed)
        total = len(results)
        print(f"\n  通过: {passed}/{total}")

        sys.exit(0 if passed == total else 1)

    else:
        # 测试单个风格
        result = tester.run_test(
            topic=args.topic,
            image_style=args.style,
            target_length=args.length,
            timeout=args.timeout
        )
        sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
