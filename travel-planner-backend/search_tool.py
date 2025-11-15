import re
import json
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, RequestsWrapper
from openai import OpenAI

# ====== OpenAI 基础配置（与主 Agent 保持一致） ======
MODEL_NAME = "gpt-4o-mini"
client = OpenAI()

# === 可配置参数 ===
_MAX_RESULTS_PER_QUERY = 6         # 每条查询取多少条
_FETCH_TOP_N_PAGES = 8             # 抓取正文的前N条（减少HTTP成本）
_TIME_WINDOW_DAYS_BEFORE = 60      # 向前最多容忍多少天的过期活动
_TIME_WINDOW_DAYS_AFTER = 75       # 向后最多容忍多少天的未来活动
_TEMPERATURE = 0.2

# 来源权重（越高越可信/热度越可能高）
_DOMAIN_BOOSTS = {
    "damai.cn": 1.25, "maoyan.com": 1.18, "piao": 1.15, "piaoxingqiu": 1.15,
    "qq.com": 1.12, "163.com": 1.12, "sina.com.cn": 1.12, "people.com.cn": 1.15,
    "gov.cn": 1.3, "edu.cn": 1.2, "org": 1.1, "museum": 1.15
}

# 关键词加权
_KEYWORD_HITS = {
    "音乐节": 1.2, "演唱会": 1.2, "展览": 1.1, "艺术": 1.08, "节": 1.06,
    "马拉松": 1.2, "比赛": 1.08, "电竞": 1.1, "嘉年华": 1.1, "车展": 1.1,
    "灯会": 1.1, "亲子": 1.06, "戏剧": 1.08, "脱口秀": 1.08
}

_DATE_PAT = re.compile(r'(?:(\d{4})年)?\s*(\d{1,2})月\s*(\d{1,2})日?')

def _now_cn():
    # 以中国时区为准，避免跨月误判
    return datetime.now(ZoneInfo("Asia/Shanghai"))

def _yyyymm_cn(dt: datetime) -> str:
    return f"{dt.year}年{dt.month}月"

def _build_queries(destination: str):
    now = _now_cn()
    prev_m = (now.replace(day=1) - timedelta(days=1)).month
    next_m = (now.replace(day=28) + timedelta(days=10)).month

    ym_now = _yyyymm_cn(now)
    ym_next = f"{now.year if next_m >= now.month else now.year+1}年{next_m}月"
    ym_prev = f"{now.year if prev_m <= now.month else now.year-1}年{prev_m}月"

    base = [
        f"{destination} {ym_now} 活动 演出 展览 赛事 节日 安排",
        f"{destination} {ym_next} 活动 演出 展览 赛事 节日",
        f"{destination} {ym_prev} 活动 演出 展览 赛事 节日",
        f"{destination} 演唱会 {ym_now}",
        f"{destination} 音乐节 {now.year}年",
        f"{destination} 展览 {ym_now}",
        f"{destination} 马拉松 赛事 {now.year}年",
        f"{destination} 亲子 活动 {ym_now}",
        f"{destination} 戏剧 话剧 演出 {ym_now}"
    ]
    # 去重保持顺序
    seen, out = set(), []
    for q in base:
        if q not in seen:
            seen.add(q); out.append(q)
    return out

def _domain_weight(url: str) -> float:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return 1.0
    for key, w in _DOMAIN_BOOSTS.items():
        if key in host:
            return w
    # 常见顶级域名微弱加权
    if host.endswith(".gov.cn"): return 1.28
    if host.endswith(".edu.cn"): return 1.2
    if host.endswith(".org"):    return 1.1
    return 1.0

def _keyword_weight(text: str) -> float:
    score = 1.0
    for k, w in _KEYWORD_HITS.items():
        if k in text:
            score *= w
    return score

def _extract_dates_zh(text: str, default_year: int) -> list:
    """粗略从文本里提取 yyyy年m月d日 / m月d日"""
    dates = []
    for m in _DATE_PAT.finditer(text):
        y = int(m.group(1)) if m.group(1) else default_year
        mon = int(m.group(2)); day = int(m.group(3))
        try:
            dt = datetime(y, mon, day, tzinfo=ZoneInfo("Asia/Shanghai"))
            dates.append(dt)
        except Exception:
            pass
    return dates

def _recency_score(dts: list, now: datetime) -> float:
    """根据距离当前的最近日期给一个递增分；未来更高，过期但在窗口内次之"""
    if not dts:
        return 1.0
    deltas = [ (dt - now).days for dt in dts ]
    best = min(deltas, key=lambda x: abs(x))
    # 未来：1.4 ~ 1.15；近过去：1.2 ~ 1.05；很远：1.0
    if best >= 0:
        return max(1.15, min(1.4, 1.4 - best * 0.004))
    else:
        return max(1.05, min(1.2, 1.2 + best * 0.004))  # best<0

def _in_time_window(dts: list, now: datetime) -> bool:
    if not dts:
        return True  # 没识别出日期时，不强行丢弃
    for dt in dts:
        if now - timedelta(days=_TIME_WINDOW_DAYS_BEFORE) <= dt <= now + timedelta(days=_TIME_WINDOW_DAYS_AFTER):
            return True
    return False

def _clean_html(html: str, limit: int = 3000) -> str:
    # 粗清洗，去标签，截断
    txt = re.sub(r'<script.*?>.*?</script>', ' ', html, flags=re.S|re.I)
    txt = re.sub(r'<style.*?>.*?</style>', ' ', txt, flags=re.S|re.I)
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt[:limit]

def search_city_hotspots(destination: str) -> dict:
    """搜索城市近期热点事件/活动并按热度排名。
    返回: {"hotspots": [ {id,title,rank,category,description} ]}
    """
    print(f"[Tool] Searching city hotspots for {destination}")
    now = _now_cn()
    current_date = now.strftime("%Y年%m月")
    try:
        # --- 搜索器（优先 Tavily，其次 DuckDuckGo）---
        # if os.getenv("TAVILY_API_KEY"):
        #     searcher = TavilySearchAPIWrapper(k=_MAX_RESULTS_PER_QUERY)
        #     use_tavily = True
        # else:
        searcher = DuckDuckGoSearchAPIWrapper(
            region="cn-zh",  # 如遇兼容问题可换 "zh-cn"
            time="m",
            safesearch="moderate",
            max_results=_MAX_RESULTS_PER_QUERY
        )
        use_tavily = False

        queries = _build_queries(destination)
        print(f"[Tool] Built {len(queries)} queries")

        # --- 汇总结果 ---
        all_hits = []  # {"title","link","snippet","query"}
        seen_links = set()
        for q in queries:
            if use_tavily:
                # Tavily 返回 [{title,url,content}]
                res = searcher.results(q)
                for r in (res or []):
                    link = r.get("url") or r.get("link")
                    if not link or link in seen_links: 
                        continue
                    seen_links.add(link)
                    all_hits.append({
                        "title": r.get("title","").strip(),
                        "link": link,
                        "snippet": (r.get("content") or r.get("snippet") or "").strip(),
                        "query": q
                    })
            else:
                res = searcher.results(q, max_results=_MAX_RESULTS_PER_QUERY)
                for r in (res or []):
                    link = r.get("link")
                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)
                    all_hits.append({
                        "title": r.get("title","").strip(),
                        "link": link,
                        "snippet": (r.get("snippet") or "").strip(),
                        "query": q
                    })

        if not all_hits:
            raise RuntimeError("No hotspot search results")

        # --- 抓取正文（前N条）并做轻度评分 ---
        requester = RequestsWrapper()
        enriched = []
        for i, h in enumerate(all_hits):
            body = ""
            if i < _FETCH_TOP_N_PAGES:
                try:
                    resp = requester.get(h["link"])
                    if resp and hasattr(resp, "text"):
                        body = _clean_html(resp.text)
                except Exception:
                    pass

            # 组合作为评分依据
            text_for_scoring = f"{h['title']} {h['snippet']} {body}"
            dates = _extract_dates_zh(text_for_scoring, default_year=now.year)

            if not _in_time_window(dates, now):
                # 严格过滤超出窗口很远的
                continue

            score = _domain_weight(h["link"]) * _keyword_weight(text_for_scoring) * _recency_score(dates, now)
            enriched.append({**h, "body": body, "dates": dates, "score": score})

        if not enriched:
            raise RuntimeError("Empty after time-window filtering")

        # --- 准备给 LLM 的上下文（控制长度与噪声）---
        # 将若干最高分候选拼接上下文
        enriched_sorted = sorted(enriched, key=lambda x: x["score"], reverse=True)[:16]

        def fmt_item(idx, it):
            host = urlparse(it["link"]).netloc
            # 只提供最多 600 字符上下文，避免提示词太长
            ctx = (it["body"] or it["snippet"])[:600]
            return (
                f"[{idx}] 标题：{it['title']}\n"
                f"来源：{host}\n"
                f"链接：{it['link']}\n"
                f"线索（片段）：{ctx}\n"
                f"---"
            )

        context_block = "\n".join([fmt_item(i+1, it) for i, it in enumerate(enriched_sorted)])

        # --- 组织提示词（严格 JSON，强调时间与来源）---
        system_prompt = "你是专业的中文本地活动策展助手，擅长从检索结果中提炼近期/即将发生的活动。"
        user_prompt = f"""当前日期：{current_date}

根据下列与“{destination}”有关的检索片段，提取并整理该城市 **5–8 个最近或即将发生** 的热点活动
（活动类型含：演出/演唱会、音乐节、展览、节庆、赛事、亲子/艺术类等）。
**必须优先**包含时间在当前月份前后 1–2 个月内的活动；其次才考虑更早/更晚的。
排序规则（rank=1 最热/最相关）：
1) 明确给出“具体日期或时间区间”的优先；
2) 即将发生（未来）的优先，其次是刚刚发生/正在进行；
3) 来源更可信（官方/票务/主流媒体）优先；
4) 更大体量/更具城市吸引力（音乐节/演唱会/赛事/大型展会）优先。

检索片段（供你判断与引用来源用）：
{context_block}

请输出严格 JSON（不要任何多余文本）：
{{
  "hotspots": [
    {{
      "title": "活动名称（中文）",
      "category": "类型（演唱会/展览/节庆/赛事/演出/亲子…）",
      "rank": 1,
      "description": "一句话简介，**包含具体时间**（如“11月21-24日，…举办”）与地点要点",
      "source_url": "原始链接（从上面片段选最可信的一条）"
    }}
  ]
}}

限制：
- rank 必须从 1 连续递增；
- title 必须中文；
- 强调“时间在近 1–2 个月内”的活动；
- 只输出 JSON。
"""

        # --- 调用模型，强制 JSON ---
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=_TEMPERATURE,
            # 如果你的 OpenAI/ Azure 客户端支持，打开下行保证 JSON 结构
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        txt = resp.choices[0].message.content or ""
        data = json.loads(txt)  # 有 response_format 时可直接解析；否则可加 robust 兜底
        hotspots_raw = data.get("hotspots", [])
        if not hotspots_raw:
            raise RuntimeError("No hotspots in model response")

        # --- 构造最终返回，生成稳定 id，裁剪到 8 条 ---
        hotspots = []
        for i, h in enumerate(hotspots_raw[:8], start=1):
            title = h.get("title", "").strip() or "未知热点"
            desc = h.get("description", "").strip() or "热门城市活动"
            cat = h.get("category", "").strip() or "活动"
            # 用标题+（可能的）日期哈希生成稳定 id
            hid = "hot_" + hashlib.md5(f"{title}-{desc}".encode("utf-8")).hexdigest()[:8]
            hotspots.append({
                "id": hid,
                "title": title,
                "rank": i,
                "category": cat,
                "description": desc
            })

        return {"hotspots": hotspots}

    except Exception as e:
        print(f"[Tool] search_city_hotspots error: {e}")
        # 兜底返回（与你现有一致）
        return {"hotspots": [
            {"id": "hot_fallback_1", "title": f"{destination} 城市灯光秀", "rank": 1, "category": "演出", "description": "夜间灯光秀吸引大量游客"},
            {"id": "hot_fallback_2", "title": f"{destination} 美食文化节", "rank": 2, "category": "美食", "description": "汇集地方特色美食摊位"},
            {"id": "hot_fallback_3", "title": f"{destination} 国际展览会", "rank": 3, "category": "展览", "description": "大型主题展览，引领潮流"}
        ]}
