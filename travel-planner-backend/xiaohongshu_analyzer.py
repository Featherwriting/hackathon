"""
小红书文章与评论分析工具
用于检索景点/餐厅相关文章，汇总用户评论并生成综合评分报告
"""

import json
import re
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI

# ====== 配置 ======
MODEL_NAME = "gpt-4o-mini"
client = OpenAI()

# 小红书数据文件路径（可根据实际调整）
NOTES_FILE = Path(__file__).parent / "data" / "search_contents_2025-11-16.json"
COMMENTS_FILE = Path(__file__).parent / "data" / "search_comments_2025-11-16.json"

# 缓存数据
_notes_cache: Optional[List[Dict]] = None
_comments_cache: Optional[Dict[str, List[Dict]]] = None


def _parse_chinese_number(num_str: str) -> int:
    """
    将中文数字字符串转换为整数
    例: "4.2万" -> 42000, "1356" -> 1356
    """
    if not num_str:
        return 0
    
    num_str = str(num_str).strip()
    
    try:
        # 处理"万"单位
        if '万' in num_str:
            base = float(num_str.replace('万', ''))
            return int(base * 10000)
        # 处理"千"单位  
        elif '千' in num_str:
            base = float(num_str.replace('千', ''))
            return int(base * 1000)
        # 直接是数字
        else:
            return int(float(num_str))
    except (ValueError, AttributeError):
        return 0


def _load_notes() -> List[Dict]:
    """
    加载小红书文章库
    预期格式: [{"note_id": "...", "title": "...", "desc": "...", "nickname": "...", "liked_count": "...", ...}, ...]
    """
    global _notes_cache
    if _notes_cache is not None:
        return _notes_cache
    
    if not NOTES_FILE.exists():
        print(f"[XHS] Notes file not found: {NOTES_FILE}")
        return []
    
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            _notes_cache = json.load(f)
        print(f"[XHS] Loaded {len(_notes_cache)} notes")
        return _notes_cache
    except Exception as e:
        print(f"[XHS] Error loading notes: {e}")
        return []


def _load_comments() -> Dict[str, List[Dict]]:
    """
    加载小红书评论库
    预期格式: [{"note_id": "...", "comment_id": "...", "content": "...", "like_count": "...", ...}, ...]
    返回: {note_id: [comments]}
    """
    global _comments_cache
    if _comments_cache is not None:
        return _comments_cache
    
    if not COMMENTS_FILE.exists():
        print(f"[XHS] Comments file not found: {COMMENTS_FILE}")
        return {}
    
    try:
        with open(COMMENTS_FILE, 'r', encoding='utf-8') as f:
            comments_list = json.load(f)
        
        # 按 note_id 分组
        comments_by_note: Dict[str, List[Dict]] = {}
        for comment in comments_list:
            note_id = comment.get("note_id")
            if note_id:
                if note_id not in comments_by_note:
                    comments_by_note[note_id] = []
                comments_by_note[note_id].append(comment)
        
        _comments_cache = comments_by_note
        print(f"[XHS] Loaded comments for {len(_comments_cache)} notes")
        return _comments_cache
    except Exception as e:
        print(f"[XHS] Error loading comments: {e}")
        return {}


def _search_relevant_notes(query: str, top_k: int = 10) -> List[Dict]:
    """
    根据查询词（景点/餐厅名称）搜索相关文章
    简单实现：关键词匹配 + 点赞数排序
    """
    notes = _load_notes()
    if not notes:
        return []
    
    # 关键词匹配
    query_keywords = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', query.lower()))
    
    scored_notes = []
    for note in notes:
        title = str(note.get("title", "")).lower()
        content = str(note.get("desc", "")).lower()  # 实际字段是 desc
        text = f"{title} {content}"
        
        # 计算匹配度
        matches = sum(1 for kw in query_keywords if kw in text)
        if matches == 0:
            continue
        
        # 综合评分：匹配度 + 点赞数
        likes = _parse_chinese_number(note.get("liked_count", "0"))  # 实际字段是 liked_count
        score = matches * 10 + likes * 0.01
        
        scored_notes.append({
            **note,
            "_relevance_score": score
        })
    
    # 按评分排序
    scored_notes.sort(key=lambda x: x["_relevance_score"], reverse=True)
    return scored_notes[:top_k]


def _aggregate_comments(note_ids: List[str]) -> List[Dict]:
    """
    聚合多篇文章的评论
    返回: [{"note_id": "...", "content": "...", "likes": 0}, ...]
    """
    comments_by_note = _load_comments()
    
    all_comments = []
    for note_id in note_ids:
        if note_id in comments_by_note:
            all_comments.extend(comments_by_note[note_id])
    
    # 按点赞数排序，取高赞评论
    all_comments.sort(key=lambda x: _parse_chinese_number(x.get("like_count", "0")), reverse=True)
    return all_comments[:50]  # 最多取前50条高赞评论


def _format_notes_for_llm(notes: List[Dict], comments: List[Dict]) -> str:
    """
    将文章和评论格式化为 LLM 可读的上下文
    """
    context = "【相关小红书文章】\n\n"
    
    for i, note in enumerate(notes[:5], 1):  # 最多展示5篇
        title = note.get("title", "无标题")
        content = note.get("desc", "")[:300]  # 实际字段是 desc，截取前300字
        author = note.get("nickname", "匿名")  # 实际字段是 nickname
        likes = note.get("liked_count", "0")  # 实际字段是 liked_count
        note_id = note.get("note_id", "")
        
        context += f"文章{i}：《{title}》\n"
        context += f"作者：{author} | 点赞：{likes}\n"
        context += f"内容摘要：{content}...\n"
        context += f"note_id: {note_id}\n\n"
    
    context += "\n【用户评论精选】\n\n"
    
    for i, comment in enumerate(comments[:20], 1):  # 最多展示20条评论
        content = comment.get("content", "")
        likes = comment.get("like_count", "0")  # 实际字段是 like_count
        context += f"{i}. {content} (👍 {likes})\n"
    
    return context


def analyze_xiaohongshu_media_score(spot_name: str, city: str = "") -> Dict:
    """
    分析小红书上关于某个景点/餐厅的媒体评分
    
    Args:
        spot_name: 景点或餐厅名称
        city: 城市名称（可选，用于提高搜索精度）
    
    Returns:
        {
            "success": bool,
            "spot_name": str,
            "summary": str,  # 综合评分总结
            "rating": float,  # 1-5 分
            "article_count": int,  # 找到的相关文章数
            "comment_count": int,  # 分析的评论数
            "top_articles": [{"title": "...", "url": "...", "note_id": "..."}],
            "highlights": [str],  # 亮点
            "concerns": [str],  # 注意事项
        }
    """
    print(f"[XHS Analyzer] Analyzing '{spot_name}' in '{city}'")
    
    # 构建查询
    query = f"{city} {spot_name}" if city else spot_name
    
    # 搜索相关文章
    relevant_notes = _search_relevant_notes(query, top_k=10)
    
    if not relevant_notes:
        return {
            "success": False,
            "spot_name": spot_name,
            "summary": f"未找到关于「{spot_name}」的小红书文章。",
            "rating": 0.0,
            "article_count": 0,
            "comment_count": 0,
            "top_articles": [],
            "highlights": [],
            "concerns": []
        }
    
    # 聚合评论
    note_ids = [n["note_id"] for n in relevant_notes if "note_id" in n]
    comments = _aggregate_comments(note_ids)
    
    # 格式化为 LLM 上下文
    context = _format_notes_for_llm(relevant_notes, comments)
    
    # 使用 LLM 生成分析报告
    system_prompt = """你是一个专业的旅游与餐饮评价分析师。你的任务是根据小红书文章和用户评论，生成综合评分报告。

请分析以下内容并以 JSON 格式返回结果：
- rating: 综合评分（1-5分，小数）
- summary: 一句话总结（50字内）
- highlights: 3-5个亮点（数组，每个10-20字）
- concerns: 2-3个注意事项或不足（数组，每个10-20字，如果没有负面评价可为空）

只返回 JSON，不要其他文字。"""
    
    user_prompt = f"""目标地点：{spot_name}

{context}

请基于以上小红书文章与评论，生成综合评分报告（JSON格式）。"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        result_text = response.choices[0].message.content
        analysis = json.loads(result_text)
        
        # 提取热门文章链接（使用实际的 note_url 字段）
        top_articles = []
        for note in relevant_notes[:3]:
            note_id = note.get("note_id", "")
            title = note.get("title", "无标题")
            # 使用实际的 note_url 字段，如果没有则构造
            url = note.get("note_url", f"https://www.xiaohongshu.com/explore/{note_id}")
            top_articles.append({
                "title": title,
                "url": url,
                "note_id": note_id
            })
        
        return {
            "success": True,
            "spot_name": spot_name,
            "summary": analysis.get("summary", "综合评价较好"),
            "rating": float(analysis.get("rating", 4.0)),
            "article_count": len(relevant_notes),
            "comment_count": len(comments),
            "top_articles": top_articles,
            "highlights": analysis.get("highlights", []),
            "concerns": analysis.get("concerns", [])
        }
        
    except Exception as e:
        print(f"[XHS Analyzer] Error during LLM analysis: {e}")
        return {
            "success": False,
            "spot_name": spot_name,
            "summary": f"分析过程中出现错误：{str(e)}",
            "rating": 0.0,
            "article_count": len(relevant_notes),
            "comment_count": len(comments),
            "top_articles": [],
            "highlights": [],
            "concerns": []
        }


def format_analysis_for_user(analysis: Dict) -> str:
    """
    将分析结果格式化为用户友好的消息
    """
    if not analysis.get("success"):
        return analysis.get("summary", "分析失败")
    
    spot_name = analysis["spot_name"]
    rating = analysis["rating"]
    summary = analysis["summary"]
    highlights = analysis.get("highlights", [])
    concerns = analysis.get("concerns", [])
    articles = analysis.get("top_articles", [])
    
    # 星级显示
    stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
    
    msg = f"""
📱 小红书媒体评分分析：{spot_name}

{stars} {rating}/5.0 分

📝 综合评价：
{summary}

✨ 用户亮点：
"""
    
    for i, highlight in enumerate(highlights, 1):
        msg += f"{i}. {highlight}\n"
    
    if concerns:
        msg += "\n⚠️ 注意事项：\n"
        for i, concern in enumerate(concerns, 1):
            msg += f"{i}. {concern}\n"
    
    if articles:
        msg += "\n🔗 参考文章：\n"
        for article in articles:
            title = article["title"]
            url = article["url"]
            msg += f"• {title}\n  {url}\n"
    
    msg += f"\n（基于 {analysis['article_count']} 篇文章和 {analysis['comment_count']} 条评论分析）"
    
    return msg
