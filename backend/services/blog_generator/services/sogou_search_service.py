"""
搜狗搜索服务 — 基于腾讯云 SearchPro API

核心价值：唯一能搜索微信公众号文章的搜索引擎。
认证方式：TC3-HMAC-SHA256（手动签名，无需 tencentcloud-sdk-python）。

来源：75.07 搜狗搜索集成方案
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import requests

logger = logging.getLogger(__name__)

# 腾讯云 SearchPro API 常量
TC_SERVICE = "wsa"
TC_HOST = "wsa.tencentcloudapi.com"
TC_ENDPOINT = f"https://{TC_HOST}"
TC_ACTION = "SearchPro"
TC_VERSION = "2025-05-08"
TC_REGION = ""
TC_ALGORITHM = "TC3-HMAC-SHA256"

# 全局服务实例
_sogou_service: Optional['SogouSearchService'] = None


class SogouSearchService:
    """搜狗搜索服务 — 基于腾讯云 SearchPro API"""

    MAX_RETRIES = 3
    RETRY_BASE_WAIT = 2

    def __init__(self, secret_id: str, secret_key: str,
                 timeout: int = 10, max_results: int = 10):
        self.secret_id = secret_id or ''
        self.secret_key = secret_key or ''
        self.timeout = timeout
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.secret_id and self.secret_key)

    def search(self, query: str, max_results: int = None) -> Dict[str, Any]:
        """执行搜狗搜索"""
        if not self.is_available():
            return {'success': False, 'results': [], 'error': 'API Key 未配置'}

        cnt = max_results or self.max_results
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                data = self._call_api(query, cnt)

                # 检查 API 错误
                resp = data.get('Response', {})
                if 'Error' in resp:
                    err = resp['Error']
                    error_msg = f"{err.get('Code', 'Unknown')}: {err.get('Message', '')}"
                    logger.error(f"搜狗搜索 API 错误: {error_msg}")
                    return {'success': False, 'results': [], 'error': error_msg}

                # 解析结果
                results = self._parse_results(resp.get('Pages', []))
                return {
                    'success': True,
                    'results': results,
                    'summary': self._generate_summary(results),
                    'error': None,
                }

            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BASE_WAIT * (2 ** attempt)
                    logger.warning(
                        f"搜狗搜索失败 (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}，"
                        f"等待 {wait}s 后重试"
                    )
                    time.sleep(wait)

        logger.error(f"搜狗搜索最终失败 ({self.MAX_RETRIES} 次重试): {last_error}")
        return {'success': False, 'results': [], 'error': str(last_error)}

    def _call_api(self, query: str, cnt: int) -> Dict:
        """调用腾讯云 SearchPro API（TC3-HMAC-SHA256 签名）"""
        payload = json.dumps({"Query": query, "Mode": 0, "Cnt": cnt})
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        date_str = now.strftime("%Y-%m-%d")

        # 1. 拼接规范请求串
        ct = "application/json; charset=utf-8"
        signed_headers = "content-type;host"
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical = (
            f"POST\n/\n\ncontent-type:{ct}\nhost:{TC_HOST}\n\n"
            f"{signed_headers}\n{payload_hash}"
        )

        # 2. 拼接待签名字符串
        scope = f"{date_str}/{TC_SERVICE}/tc3_request"
        string_to_sign = (
            f"{TC_ALGORITHM}\n{timestamp}\n{scope}\n"
            f"{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        )

        # 3. 计算签名
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = _hmac_sha256(f"TC3{self.secret_key}".encode("utf-8"), date_str)
        secret_service = _hmac_sha256(secret_date, TC_SERVICE)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # 4. 构造 Authorization
        auth = (
            f"{TC_ALGORITHM} Credential={self.secret_id}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        headers = {
            "Authorization": auth,
            "Content-Type": ct,
            "Host": TC_HOST,
            "X-TC-Action": TC_ACTION,
            "X-TC-Version": TC_VERSION,
            "X-TC-Timestamp": str(timestamp),
        }
        if TC_REGION:
            headers["X-TC-Region"] = TC_REGION

        resp = requests.post(TC_ENDPOINT, headers=headers, data=payload,
                             timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _parse_results(self, pages: List) -> List[Dict[str, Any]]:
        """解析 Pages 列表，统一格式并标记微信来源"""
        results = []
        for page_str in pages:
            try:
                page = json.loads(page_str) if isinstance(page_str, str) else page_str
                url = page.get('url', '')
                is_wechat = 'mp.weixin.qq.com' in url
                results.append({
                    'title': page.get('title', ''),
                    'url': url,
                    'content': page.get('passage', ''),
                    'date': page.get('date', ''),
                    'source': '搜狗搜索',
                    'source_type': 'wechat' if is_wechat else 'web',
                })
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"搜狗结果解析失败: {e}")
        return results

    def _generate_summary(self, results: List[Dict]) -> str:
        if not results:
            return ''
        parts = []
        for item in results:
            src = item.get('source', '搜狗搜索')
            st = item.get('source_type', 'web')
            tag = f"[{src}|{st}]" if st == 'wechat' else f"[{src}]"
            parts.append(f"{tag} {item.get('title', '')}\n{item.get('content', '')[:800]}")
        return '\n\n---\n\n'.join(parts)


def init_sogou_service(config: Dict = None) -> Optional[SogouSearchService]:
    """初始化搜狗搜索服务"""
    global _sogou_service
    secret_id = os.environ.get('TENCENTCLOUD_SECRET_ID', '')
    secret_key = os.environ.get('TENCENTCLOUD_SECRET_KEY', '')

    if not secret_id or not secret_key:
        logger.info("搜狗搜索: TENCENTCLOUD_SECRET_ID/KEY 未配置，跳过")
        _sogou_service = None
        return None

    timeout = int(os.environ.get('SOGOU_SEARCH_TIMEOUT', '10'))
    max_results = int(os.environ.get('SOGOU_MAX_RESULTS', '10'))
    _sogou_service = SogouSearchService(
        secret_id=secret_id, secret_key=secret_key,
        timeout=timeout, max_results=max_results,
    )
    logger.info("搜狗搜索服务已初始化")
    return _sogou_service


def get_sogou_service() -> Optional[SogouSearchService]:
    """获取搜狗搜索服务实例"""
    return _sogou_service
