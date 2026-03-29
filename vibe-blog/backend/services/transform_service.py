"""
内容转化服务 - 将技术博客转化为通俗易懂的科普绘本风格
"""
import json
import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """单页内容"""
    page_number: int
    title: str
    content: str
    metaphor: str = ""  # 比喻说明
    image_description: str = ""  # 配图描述
    tech_note: str = ""  # 技术要点（折叠）
    mapping: Dict[str, str] = field(default_factory=dict)  # 比喻映射


@dataclass
class TransformResult:
    """转化结果"""
    title: str
    subtitle: str = ""
    core_metaphor: str = ""  # 核心比喻
    target_audience: str = "技术小白"
    total_pages: int = 0
    pages: List[PageContent] = field(default_factory=list)
    style: str = "可爱卡通风"


class TransformService:
    """内容转化服务"""
    
    # 技术概念比喻库
    METAPHOR_LIBRARY = {
        "redis": ("便利店", "东西少但拿得快，就在楼下随时可用"),
        "mysql": ("大超市", "东西全但要排队，开车去比较远"),
        "数据库": ("大超市", "存放所有商品的地方"),
        "缓存": ("便利店", "把常用的东西放在手边"),
        "消息队列": ("快递驿站", "发件人不用等收件人在家"),
        "kafka": ("快递驿站", "超大型快递中转站，吞吐量惊人"),
        "分布式锁": ("公共厕所的锁", "一次只能一个人用"),
        "负载均衡": ("银行叫号机", "哪个窗口空就去哪个"),
        "索引": ("书的目录", "不用翻遍全书找内容"),
        "微服务": ("专业分工的餐厅", "切菜的切菜，炒菜的炒菜"),
        "容器": ("集装箱", "不管里面装什么，箱子规格统一"),
        "docker": ("集装箱", "标准化的打包方式"),
        "api": ("餐厅菜单", "告诉你能点什么，怎么点"),
        "cdn": ("连锁便利店", "全国各地都有分店，就近取货"),
        "dns": ("114查号台", "告诉你电话号码在哪"),
        "tcp": ("寄快递", "写地址、打包、发货、签收，确保送达"),
        "http": ("打电话", "你说一句我答一句"),
        "websocket": ("对讲机", "随时都能说话，不用挂断"),
        "事务": ("银行转账", "要么都成功，要么都失败"),
        "缓存穿透": ("故意问没有的商品", "便利店没有还要去超市查"),
        "缓存雪崩": ("便利店突然关门", "所有人都涌向超市"),
        "限流": ("景区限流", "人太多就不让进了"),
        "熔断": ("保险丝", "电流太大自动断开保护"),
        "降级": ("餐厅太忙只卖盖饭", "忙不过来就简化服务"),
        "线程": ("工人", "干活的人"),
        "进程": ("工厂", "独立运行的车间"),
        "锁": ("钥匙", "拿到钥匙才能进门"),
        "死锁": ("两个人互相等对方让路", "谁都不让，都走不了"),
        "内存": ("工作台", "正在用的东西放这里"),
        "硬盘": ("仓库", "长期存放的地方"),
        "cpu": ("大脑", "负责思考和计算"),
        "gpu": ("流水线工人", "同时干很多重复的活"),
        "算法": ("菜谱", "按步骤做事的方法"),
        "递归": ("俄罗斯套娃", "打开一个还有一个"),
        "哈希": ("身份证号", "每个人都有唯一的编号"),
        "队列": ("排队", "先来先服务"),
        "栈": ("叠盘子", "后放的先拿"),
        "树": ("家谱", "有父子关系的结构"),
        "图": ("地铁线路图", "站点之间有连接"),
    }
    
    def __init__(self, llm_service):
        """
        初始化转化服务
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm_service = llm_service
    
    def transform(
        self,
        content: str,
        title: str = "",
        target_audience: str = "技术小白",
        style: str = "可爱卡通风",
        page_count: int = 8,
        on_chunk: callable = None
    ) -> Dict[str, Any]:
        """
        将技术内容转化为科普绘本风格
        
        Args:
            content: 原始技术博客内容
            title: 标题（可选，会自动提取）
            target_audience: 目标受众
            style: 视觉风格
            page_count: 目标页数
            on_chunk: 流式输出回调
            
        Returns:
            转化结果字典
        """
        try:
            logger.info(f"=== 开始内容转化 ===")
            logger.info(f"内容长度: {len(content)} 字符")
            logger.info(f"目标受众: {target_audience}")
            logger.info(f"目标页数: {page_count}")
            
            # 1. 分析内容，提取技术概念
            tech_concepts = self._extract_tech_concepts(content)
            logger.info(f"提取到技术概念: {tech_concepts}")
            
            # 2. 查找或生成比喻
            metaphors = self._find_metaphors(tech_concepts)
            logger.info(f"找到比喻: {metaphors}")
            
            # 3. 生成科普绘本内容
            result = self._generate_storybook(
                content=content,
                title=title,
                tech_concepts=tech_concepts,
                metaphors=metaphors,
                target_audience=target_audience,
                style=style,
                page_count=page_count,
                on_chunk=on_chunk
            )
            
            logger.info(f"=== 转化完成 ===")
            logger.info(f"生成标题: {result.get('title')}")
            logger.info(f"总页数: {result.get('total_pages')}")
            
            return {
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"内容转化失败: {e}", exc_info=True)
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def _extract_tech_concepts(self, content: str) -> List[str]:
        """从内容中提取技术概念"""
        concepts = []
        content_lower = content.lower()
        
        # 从比喻库中匹配
        for keyword in self.METAPHOR_LIBRARY.keys():
            if keyword in content_lower:
                concepts.append(keyword)
        
        # 如果没找到，尝试用 LLM 提取
        if not concepts and self.llm_service:
            prompt = f"""从以下技术文章中提取3-5个核心技术概念（只返回概念名称，用逗号分隔）：

{content[:2000]}

核心技术概念："""
            
            response = self.llm_service.chat([
                {"role": "user", "content": prompt}
            ])
            
            if response:
                concepts = [c.strip() for c in response.split(',') if c.strip()]
        
        return concepts[:5]  # 最多5个
    
    def _find_metaphors(self, concepts: List[str]) -> Dict[str, tuple]:
        """为技术概念查找比喻"""
        metaphors = {}
        for concept in concepts:
            concept_lower = concept.lower()
            if concept_lower in self.METAPHOR_LIBRARY:
                metaphors[concept] = self.METAPHOR_LIBRARY[concept_lower]
        return metaphors
    
    def _generate_storybook(
        self,
        content: str,
        title: str,
        tech_concepts: List[str],
        metaphors: Dict[str, tuple],
        target_audience: str,
        style: str,
        page_count: int,
        on_chunk: callable = None
    ) -> Dict[str, Any]:
        """使用 LLM 生成科普绘本内容"""
        
        # 构建比喻提示
        metaphor_hints = ""
        if metaphors:
            metaphor_hints = "\n可用的比喻参考：\n"
            for concept, (metaphor, explanation) in metaphors.items():
                metaphor_hints += f"- {concept} → {metaphor}：{explanation}\n"
        
        system_prompt = """你是一个技术科普专家，擅长用生活化的比喻把复杂技术讲得通俗易懂。

你的任务是将技术博客转化为"技术科普绘本"风格的内容，让完全不懂技术的小白也能看懂。

## 写作原则

1. **用生活比喻**：每个技术概念都要找到生活中的类比
2. **讲故事**：用场景代入，让读者有画面感
3. **简单直白**：避免专业术语，用大白话
4. **有趣幽默**：适当加入轻松的表达
5. **循序渐进**：从简单到复杂，一步步引导

## 输出格式

请输出 JSON 格式，结构如下：
```json
{
  "title": "标题（要有趣，能吸引人）",
  "subtitle": "副标题（用比喻概括）",
  "core_metaphor": "核心比喻（一句话说明整体类比）",
  "pages": [
    {
      "page_number": 1,
      "title": "页面标题",
      "content": "页面正文（100-150字，通俗易懂）",
      "metaphor": "本页使用的比喻",
      "image_description": "配图描述（用于生成插图）",
      "tech_note": "技术要点（可折叠，给想深入的读者）",
      "mapping": {"比喻元素": "技术概念"}
    }
  ]
}
```"""

        user_prompt = f"""请将以下技术博客转化为{page_count}页的技术科普绘本。

目标读者：{target_audience}
视觉风格：{style}
{metaphor_hints}

## 原始技术内容

{content}

## 要求

1. 生成{page_count}页内容
2. 第1页是引子（用问题或场景引入）
3. 中间页面逐步讲解核心概念
4. 最后1页是总结
5. 每页都要有配图描述
6. 保持比喻的一致性

请输出 JSON 格式的科普绘本内容："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用 LLM
        if on_chunk and hasattr(self.llm_service, 'chat_stream'):
            response = self.llm_service.chat_stream(
                messages=messages,
                temperature=0.7,
                on_chunk=on_chunk
            )
        else:
            response = self.llm_service.chat(
                messages=messages,
                temperature=0.7
            )
        
        if not response:
            raise Exception("LLM 调用失败")
        
        # 解析 JSON 响应
        result = self._parse_json_response(response)
        
        # 补充默认值
        result.setdefault('title', title or '技术科普')
        result.setdefault('subtitle', '')
        result.setdefault('core_metaphor', '')
        result.setdefault('target_audience', target_audience)
        result.setdefault('style', style)
        result.setdefault('pages', [])
        result['total_pages'] = len(result.get('pages', []))
        
        return result
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response.strip()
            # 如果以 { 开头，找到匹配的 }
            if json_str.startswith('{'):
                # 找到最后一个 }
                last_brace = json_str.rfind('}')
                if last_brace > 0:
                    json_str = json_str[:last_brace + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.error(f"原始响应: {response[:500]}...")
            # 返回基本结构
            return {
                'title': '技术科普',
                'pages': [],
                'raw_response': response
            }
    
    def get_metaphor(self, concept: str) -> Optional[tuple]:
        """获取单个概念的比喻"""
        return self.METAPHOR_LIBRARY.get(concept.lower())
    
    def add_metaphor(self, concept: str, metaphor: str, explanation: str):
        """添加新的比喻到库中"""
        self.METAPHOR_LIBRARY[concept.lower()] = (metaphor, explanation)


def create_transform_service(llm_service) -> TransformService:
    """创建转化服务实例"""
    return TransformService(llm_service=llm_service)
