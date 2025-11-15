"""
LangGraph-based Travel Planning Agent
智能旅行规划 Agent，能够逐步询问用户需求并生成动态行程计划
"""

from typing import TypedDict
from datetime import datetime
import json
import re
import httpx
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from openai import OpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from search_tool import search_city_hotspots

# ====== 初始化 OpenAI Client ======
client = OpenAI()
MODEL_NAME = "gpt-4o-mini"  # 或使用 "gpt-3.5-turbo" 以降低成本

# ====== 定义 Agent 状态 ======

class TravelPlanState(TypedDict):
    """Agent 的工作状态"""
    messages: list  # 对话历史
    destination: str  # 目的地城市
    days: int  # 旅行天数
    people_count: int  # 人数
    interests: list[str]  # 兴趣爱好（美食、景点、购物等）
    budget: str  # 预算等级（低/中/高）
    itinerary: dict  # 生成的行程计划
    featured_spots: list[dict]  # 推荐景点
    city_hotspots: list[dict]  # 城市最新热点/活动
    current_phase: str  # 当前对话阶段（greeting/gathering_info/generating_plan/refining）
    info_complete: bool  # 是否获取了足够的信息


# ====== 行程规划辅助函数（智能版） ======

def _estimate_duration_hours(spot: dict) -> int:
    """
    根据景点类型粗略估算停留时间（小时）
    """
    category = str(spot.get("category", ""))

    if any(k in category for k in ["户外", "郊游", "自然", "公园", "山"]):
        return 4
    if any(k in category for k in ["景点", "游览", "观光"]):
        return 3
    if any(k in category for k in ["博物馆", "美术馆", "文化", "历史"]):
        return 2
    if any(k in category for k in ["购物", "商场", "商业"]):
        return 2
    if any(k in category for k in ["美食", "餐厅", "小吃", "街"]):
        return 1

    # 默认 2 小时
    return 2


def _score_and_sort_spots(spots: list[dict], interests: list[str], budget: str) -> list[dict]:
    """
    给每个景点打分并按分数排序（热门程度 + 兴趣匹配 + 预算轻微影响）
    """
    if not spots:
        return []

    interests = interests or []
    normalized_interests = [str(i) for i in interests]

    scored: list[dict] = []
    for idx, s in enumerate(spots):
        rating = float(s.get("rating", 4.5) or 4.5)
        category = str(s.get("category", ""))
        title = str(s.get("title", ""))

        # 兴趣匹配：如果兴趣关键词出现在类别或标题中，加一档权重
        interest_bonus = 0.0
        for it in normalized_interests:
            if it and (it in category or it in title):
                interest_bonus = 1.0
                break

        # 用原始顺序当作热度衰减（越靠前越热门）
        base_popularity = max(0.3, 1.0 - idx * 0.05)

        # 预算对高评分景点稍微增益（预算高的更偏向“值得一去”的）
        budget_factor = 1.0
        if budget == "高":
            budget_factor = 1.05
        elif budget == "低":
            budget_factor = 0.95

        score = (rating * 0.6 + interest_bonus * 0.3 + base_popularity * 0.1) * budget_factor
        s_copy = dict(s)
        s_copy["_score"] = score
        scored.append(s_copy)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored


def _apply_interest_ratio(
    sorted_spots: list[dict],
    interests: list[str],
    max_interest_ratio: float = 0.6,
) -> list[dict]:
    """
    在已经按综合得分排序好的景点列表上，控制“符合兴趣偏好”的景点在
    整体顺序中的占比，但 **不删除任何景点**，只调整顺序。

    目标效果：
    - 大约不超过 max_interest_ratio 比例是兴趣类（美食等）
    - 保证有足够的非兴趣类混进去
    - 景点总数保持不变
    """
    if not sorted_spots or not interests:
        return sorted_spots

    interests = [str(i) for i in interests if i]

    def is_interest_spot(s: dict) -> bool:
        cat = str(s.get("category", ""))
        title = str(s.get("title", ""))
        text = cat + " " + title
        return any(it and it in text for it in interests)

    interest_spots: list[dict] = []
    other_spots: list[dict] = []

    for s in sorted_spots:
        if is_interest_spot(s):
            interest_spots.append(s)
        else:
            other_spots.append(s)

    total = len(sorted_spots)
    if total == 0:
        return sorted_spots

    # 目标：兴趣类最多占这么多比例
    target_interest_max = int(total * max_interest_ratio)
    if target_interest_max == 0 and interest_spots:
        target_interest_max = 1  # 至少留 1 个兴趣类

    # 交替从兴趣 / 非兴趣池子中取，控制“前面这段”的比例
    result: list[dict] = []
    i_idx = 0
    o_idx = 0
    interest_used = 0

    while i_idx < len(interest_spots) or o_idx < len(other_spots):
        used = len(result)

        # 当前兴趣比例
        current_ratio = (interest_used / used) if used > 0 else 0.0

        # 如果兴趣比例还没到上限而且还有兴趣点，就优先取兴趣点
        take_interest = (
            i_idx < len(interest_spots)
            and (interest_used < target_interest_max)
            and (current_ratio <= max_interest_ratio)
        )

        if take_interest:
            result.append(interest_spots[i_idx])
            i_idx += 1
            interest_used += 1
        elif o_idx < len(other_spots):
            result.append(other_spots[o_idx])
            o_idx += 1
        else:
            # 其他点用完了，只能继续放兴趣点了
            result.append(interest_spots[i_idx])
            i_idx += 1
            interest_used += 1

    # 长度保持不变
    return result


def _split_spots_by_day(sorted_spots: list[dict], days: int) -> list[list[dict]]:
    """
    根据停留时长与天数，把景点拆分到每天，尽量保证每天 6~9 小时内容
    """
    if days <= 0:
        return []

    day_buckets: list[list[dict]] = [[] for _ in range(days)]
    day_hours = [0 for _ in range(days)]

    # 贪心：每次把下一个景点放到当前总时长最少的一天
    for s in sorted_spots:
        dur = _estimate_duration_hours(s)
        # 找当前最空的一天
        idx = min(range(days), key=lambda i: day_hours[i])
        # 控制每天大致不超过 9 小时，如果可以的话优先填更空的那天
        if day_hours[idx] + dur > 9 and any(h < 7 for h in day_hours):
            candidates = [i for i in range(days) if day_hours[i] + dur <= 9]
            if candidates:
                idx = min(candidates, key=lambda i: day_hours[i])
        day_buckets[idx].append(s)
        day_hours[idx] += dur

    return day_buckets


def _build_day_theme_summary(spots_for_day: list[dict], destination: str) -> dict:
    """
    根据当天的景点，生成这一天的旅行主题 & 总结文案

    返回:
    {
        "total_hours": int,
        "theme": str,
        "highlights": list[str],
        "summary": str,
    }
    """
    # 没有具体景点：轻松自由行
    if not spots_for_day:
        total_hours = 6
        theme = f"轻松自由逛逛{destination}"
        highlights: list[str] = []
        summary = f"约 {total_hours} 小时 · 主题：{theme}"
        return {
            "total_hours": total_hours,
            "theme": theme,
            "highlights": highlights,
            "summary": summary,
        }

    # 1. 估算总时长
    total_hours = 0
    category_counter: dict[str, int] = {}
    for s in spots_for_day:
        dur = _estimate_duration_hours(s)
        total_hours += dur
        cat = str(s.get("category", "其他"))
        category_counter[cat] = category_counter.get(cat, 0) + 1

    # 2. 用出现次数最多的类别推主主题
    main_category = max(category_counter.items(), key=lambda x: x[1])[0]

    if any(k in main_category for k in ["美食", "餐厅", "小吃"]):
        theme = "美食探索日"
    elif any(k in main_category for k in ["户外", "自然", "公园", "山"]):
        theme = "户外 / 自然风光日"
    elif any(k in main_category for k in ["文化", "历史", "博物馆"]):
        theme = "人文历史 & 博物馆体验"
    elif any(k in main_category for k in ["购物", "商场", "商业"]):
        theme = "购物逛街 & 轻松漫步"
    else:
        theme = f"{destination} 经典景点打卡日"

    # 3. 亮点景点
    highlights = [str(s.get("title", "")) for s in spots_for_day[:2] if s.get("title")]

    # 4. 总结文案：时间 + 主题 + 亮点
    summary = f"约 {total_hours} 小时 · 主题：{theme}"
    if highlights:
        summary += f" · 亮点：{'、'.join(highlights)}"

    return {
        "total_hours": total_hours,
        "theme": theme,
        "highlights": highlights,
        "summary": summary,
    }


def _build_day_timeline(
    day_index: int,
    destination: str,
    spots_for_day: list[dict],
    budget: str
) -> list[dict]:
    """
    根据当天选定的景点构建时间轴
    输出 activities: [{id, icon, title, time, description, ref_spot_id?}]
    """
    activities: list[dict] = []

    # 图标映射
    icon_map = {
        "景点": "🗺️",
        "观光": "🗺️",
        "文化": "🏛️",
        "博物馆": "🏛️",
        "历史": "🏛️",
        "户外": "⛰️",
        "自然": "⛰️",
        "公园": "🌳",
        "美食": "🍜",
        "餐厅": "🍽️",
        "小吃": "🥟",
        "购物": "🛍️",
        "夜景": "🌉",
        "娱乐": "🎡",
    }

    def pick_icon(category: str) -> str:
        for key, ic in icon_map.items():
            if key in category:
                return ic
        return "📍"

    # 行程起止时间：大概 09:00 - 21:00
    current_hour = 9
    max_hour = 21

    # 没有景点，给一条“自由活动”
    if not spots_for_day:
        activities.append({
            "id": f"day_{day_index+1}_free",
            "icon": "😌",
            "title": f"{destination} 自由活动",
            "time": "10:00 - 16:00",
            "description": f"这一天留给你自由安排，可以慢慢逛逛{destination}的街道、咖啡馆或商场。"
        })
        return activities

    for i, s in enumerate(spots_for_day):
        duration = _estimate_duration_hours(s)
        if current_hour >= max_hour:
            break

        # 固定午餐时间段
        if 12 <= current_hour < 13:
            activities.append({
                "id": f"day_{day_index+1}_lunch",
                "icon": "🍽️",
                "title": f"{destination} 当地午餐",
                "time": "12:00 - 13:00",
                "description": f"在附近找一家评价不错的餐厅，尝试{destination}的本地风味。"
            })
            current_hour = 13

        start_hour = current_hour
        end_hour = min(current_hour + duration, max_hour)

        category = str(s.get("category", "景点"))
        title = str(s.get("title", f"{destination} 景点"))
        rating = s.get("rating", None)
        rating_text = f" · 评分 {rating}" if rating is not None else ""

        # 描述只用“约 X 小时”
        duration_text = f"建议停留约 {duration} 小时"
        desc_main = f"{category}{rating_text}。{duration_text}，并已与同区域/同类型景点放在同一天，尽量减少来回折腾。"

        activities.append({
            "id": f"day_{day_index+1}_spot_{i+1}",
            "icon": pick_icon(category),
            "title": title,
            "time": f"{start_hour:02d}:00 - {end_hour:02d}:00",
            "description": desc_main,
            "ref_spot_id": s.get("id")
        })

        current_hour = end_hour

    # 下午到晚餐之间留一点轻松时间
    if current_hour < 18:
        activities.append({
            "id": f"day_{day_index+1}_rest",
            "icon": "☕",
            "title": "咖啡小憩 & 街头漫步",
            "time": f"{current_hour:02d}:00 - 18:00",
            "description": "找一家喜欢的咖啡店或面包房，慢慢歇歇脚，再在附近街区随意走走。"
        })
        current_hour = 18

    # 晚餐/夜景：预算高一点的安排更“仪式感”
    if budget == "高":
        activities.append({
            "id": f"day_{day_index+1}_dinner",
            "icon": "🍷",
            "title": f"{destination} 精致晚餐 & 夜景",
            "time": "19:00 - 21:00",
            "description": f"选择环境与评价更好的餐厅用餐，之后可以去看一看{destination}的夜景或河岸/海边。"
        })
    else:
        activities.append({
            "id": f"day_{day_index+1}_dinner",
            "icon": "🍜",
            "title": f"{destination} 夜市 / 街头小吃",
            "time": "19:00 - 20:30",
            "description": f"逛逛夜市或人气小吃街，轻松随意地感受{destination}的夜晚。"
        })

    return activities


def generate_itinerary(
    destination: str,
    days: int,
    interests: list[str],
    budget: str,
    featured_spots: list[dict] | None = None
) -> dict:
    """
    根据用户需求生成行程计划（智能版）。

    逻辑：
    1. 对景点进行打分排序（按热门程度 + 兴趣偏好 + 预算倾向）
    2. 粗略估算每个景点停留时长
    3. 把景点拆分到每天（目标：每天约 6~9 小时）
    4. 为每天构建时间轴（09:00~21:00 左右），插入午餐、晚餐/夜景
    5. 每天生成一个 summary（约多少小时 + 旅行特色）
    6. 如果景点不足，也会生成“自由活动”占位，避免空白行程

    返回结构:
    {
      "plans": [
        {
          "id": "day_1",
          "day": "Day 1",
          "summary": "约 7 小时 · 主题：XXX · 亮点：A、B",
          "meta": {
              "total_hours": 7,
              "theme": "XXX",
              "highlights": ["A", "B"]
          },
          "activities": [...]
        },
        ...
      ]
    }
    """
    print(
        f"[Tool] Generating itinerary (smart): dest={destination}, "
        f"days={days}, interests={interests}, budget={budget}, "
        f"spots={len(featured_spots) if featured_spots else 0}"
    )

    if days <= 0:
        days = 1

    plans: list[dict] = []

    # 没有景点时，生成纯占位行程
    if not featured_spots:
        for d in range(days):
            activities = _build_day_timeline(
                day_index=d,
                destination=destination,
                spots_for_day=[],
                budget=budget
            )
            summary_info = _build_day_theme_summary([], destination)
            plans.append({
                "id": f"day_{d+1}",
                "day": f"Day {d+1}",
                "summary": summary_info["summary"],
                "meta": {
                    "total_hours": summary_info["total_hours"],
                    "theme": summary_info["theme"],
                    "highlights": summary_info["highlights"],
                },
                "activities": activities
            })
        return {"plans": plans}

    # 1. 按综合得分排序景点
    sorted_spots = _score_and_sort_spots(featured_spots, interests, budget)

    # 控制“兴趣类景点”的占比，让它大约不超过 60%
    sorted_spots = _apply_interest_ratio(sorted_spots, interests, max_interest_ratio=0.6)

    # 2. 把景点拆分到每天
    day_spot_buckets = _split_spots_by_day(sorted_spots, days)

    # 3. 为每一天构建活动时间表 + 每日 summary
    for d in range(days):
        spots_for_day = day_spot_buckets[d] if d < len(day_spot_buckets) else []

        activities = _build_day_timeline(
            day_index=d,
            destination=destination,
            spots_for_day=spots_for_day,
            budget=budget
        )
        summary_info = _build_day_theme_summary(spots_for_day, destination)

        plans.append({
            "id": f"day_{d+1}",
            "day": f"Day {d+1}",
            "summary": summary_info["summary"],  # 前端可直接展示
            "meta": {  # 想做更花的 UI 再用
                "total_hours": summary_info["total_hours"],
                "theme": summary_info["theme"],
                "highlights": summary_info["highlights"],
            },
            "activities": activities
        })

    return {"plans": plans}


def fetch_featured_spots(destination: str, interests: list[str]) -> dict:
    """
    使用网络搜索获取目的地的推荐景点。
    1. 根据兴趣在互联网上搜索景点
    2. 用 GPT 总结和整理搜索结果
    3. 返回格式: { "spots": [ {id,title,rating,category,price,image}, ... ] }
    """
    print(f"[Tool] Fetching featured spots for {destination} with interests: {interests}")

    try:
        # 构建搜索查询
        interests_str = ",".join(interests) if interests else "景点"
        search_query = f"{destination} 热门 {interests_str} 景点 旅游"

        print(f"[Tool] Searching: {search_query}")

        # 使用 LangChain DuckDuckGo 搜索工具
        search = DuckDuckGoSearchResults(
            api_wrapper=DuckDuckGoSearchAPIWrapper(region="cn-zh", max_results=10)
        )
        search_results_str = search.run(search_query)

        if not search_results_str or search_results_str.strip() == "":
            print(f"[Tool] No search results, using fallback")
            raise RuntimeError("Search returned no results")

        # LangChain 返回的是格式化字符串，直接作为上下文
        search_context = f"搜索结果:\n{search_results_str}"

        print(f"[Tool] Got search results (length: {len(search_results_str)})")

        # 用 GPT 总结和整理搜索结果成景点列表
        summary_prompt = f"""根据以下关于{destination}的搜索结果，提取出最受欢迎的景点或旅游地点。

{search_context}

请以 JSON 格式返回一个景点列表，每个景点包含：
- title: 景点名称（中文）
- category: 景点类型，如"景点"、"美食"、"购物"、"文化"等
- rating: 推荐指数，4.0-5.0 之间的浮点数
- description: 简短描述（一句话）

返回格式：
{{
  "spots": [
    {{"title": "景点名", "category": "类型", "rating": 4.5, "description": "..."}},
    ...
  ]
}}

请最多提取8个景点，并按热度排序。"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "你是一个旅行专家，擅长分析和整理旅游信息。"},
                {"role": "user", "content": summary_prompt}
            ]
        )

        response_text = response.choices[0].message.content
        print(f"[Tool] GPT Response: {response_text[:200]}...")

        # 尝试从 GPT 响应中提取 JSON
        try:
            # 查找 JSON 块
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                spots_data = parsed.get("spots", [])
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[Tool] JSON parse error: {e}, using fallback")
            # 如果 JSON 解析失败，使用本地回退数据
            spots_data = []

        # 格式化为前端所需的格式
        spots = []
        for idx, spot in enumerate(spots_data[:8], 1):
            spots.append({
                "id": f"web_{idx}",
                "title": spot.get("title", "未知景点"),
                "rating": spot.get("rating", 4.5),
                "category": spot.get("category", "景点"),
                "price": 0,
                "image": "https://via.placeholder.com/300x200?text=POI"
            })

        if spots:
            print(f"[Tool] Returning {len(spots)} spots from web search")
            return {"spots": spots}
        else:
            raise RuntimeError("No spots extracted from search results")

    except Exception as e:
        print(f"[Tool] fetch_featured_spots error: {e}")
        # 回退到本地示例数据，保证可用性
        return {"spots": [
            {"id": "fallback_1", "title": f"{destination} 热门景点", "rating": 4.6, "category": "景点", "price": 0, "image": "https://via.placeholder.com/300x200?text=Fallback"},
            {"id": "fallback_2", "title": f"{destination} 特色美食街", "rating": 4.4, "category": "美食", "price": 0, "image": "https://via.placeholder.com/300x200?text=Fallback"},
            {"id": "fallback_3", "title": f"{destination} 购物中心", "rating": 4.5, "category": "购物", "price": 0, "image": "https://via.placeholder.com/300x200?text=Fallback"},
        ]}


# ====== Agent 节点定义 ======

def node_greeting(state: TravelPlanState) -> TravelPlanState:
    """
    第一次交互：问候用户并开始收集信息
    """
    print("[Node] Greeting...")

    system_prompt = """你是一个专业的旅行规划助手。你的目标是帮助用户规划完美的旅行。

你需要通过对话逐步收集以下信息：
1. 目的地城市（destination）
2. 旅行天数（days）
3. 同行人数（people_count）
4. 兴趣爱好（interests：美食、购物、文化、景点、户外等）
5. 预算等级（budget：低/中/高）

现在，用友好热情的语气问候用户，并问他们的旅行目的地。中文回复。"""

    messages = state.get("messages", [])

    # 构建消息，包含 system prompt
    conversation_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "你好"}
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=500,
        messages=conversation_messages
    )

    assistant_message = response.choices[0].message.content

    state["messages"] = messages + [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": assistant_message}
    ]
    state["current_phase"] = "gathering_info"

    return state


def node_gather_info(state: TravelPlanState) -> TravelPlanState:
    """
    收集用户信息阶段
    """
    print("[Node] Gathering information...")
    print(f"[State] Current info: destination={state.get('destination')}, days={state.get('days')}, people_count={state.get('people_count')}, interests={state.get('interests')}, budget={state.get('budget')}")

    messages = state.get("messages", [])

    # 提取用户最后消息
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # 从最后的用户消息中提取信息
    state = extract_info_from_message(state, last_user_msg)

    # 先检查信息是否已完整，若完整则直接跳到生成阶段
    if should_generate_plan(state):
        print("[Node] Info complete, transitioning to generate plan...")
        state["current_phase"] = "generating_plan"
        state["info_complete"] = True
        # 添加一个简短的过渡消息，然后在同一次请求里调用 node_generate_plan
        transition_message = "好的，信息已收集完成！正在为您生成行程计划..."
        state["messages"].append({"role": "assistant", "content": transition_message})
        return state

    # 信息不完整，继续询问用户
    system_prompt = f"""你是一个专业的旅行规划助手。你的任务是收集用户的旅行信息。

已收集的信息：
- 目的地: {state.get("destination", "未提供")}
- 天数: {state.get("days", "未提供")}
- 人数: {state.get("people_count", "未提供")}
- 兴趣: {", ".join(state.get("interests", [])) or "未提供"}
- 预算: {state.get("budget", "未提供")}

请根据已收集的信息，礼貌地询问缺失的信息（目的地/天数/人数/兴趣/预算）。
不要生成行程、不要总结推荐。只输出简短的确认或追问句子。
使用中文回复，语气友好、简洁。"""

    # 保留完整的对话历史以保持上下文记忆
    conversation_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=250,
        messages=conversation_messages
    )

    assistant_message = response.choices[0].message.content

    state["messages"].append({"role": "assistant", "content": assistant_message})

    return state


def node_generate_plan(state: TravelPlanState) -> TravelPlanState:
    """
    生成行程计划阶段
    """
    print("[Node] Generating travel plan...")

    # 调用工具先获取景点，再根据景点生成行程，保证行程中包含被推荐的景点
    destination = state.get("destination", "香港")
    days = state.get("days", 3)
    interests = state.get("interests", ["景点"])
    budget = state.get("budget", "中")

    # 先获取推荐景点（网络搜索或回退）
    spots_result = fetch_featured_spots(destination, interests)
    featured = spots_result.get("spots", [])
    state["featured_spots"] = featured

    # 搜索城市热点并保存
    hotspots_result = search_city_hotspots(destination)
    state["city_hotspots"] = hotspots_result.get("hotspots", [])

    # 再生成行程，并把 featured_spots 传入以便嵌入到每日活动
    itinerary_result = generate_itinerary(destination, days, interests, budget, featured_spots=featured)
    state["itinerary"] = itinerary_result

    # 生成总结消息
    destination = state.get("destination", "未知")
    days = state.get("days", 0)
    people = state.get("people_count", 1)
    interests_str = ",".join(state.get("interests", [])) or "多样化"

    plan_summary = f"""
我已经为您准备好了完整的行程计划！

目的地：{destination}
天数：{days}天
人数：{people}人
兴趣：{interests_str}

我已经生成了每日详细的活动安排和热门景点推荐。这份行程根据您的偏好进行了定制化设计。
您可以在页面右侧看到"行程计划"和"热门景点"的更新。

此外，我也为您整理了近期的城市热点活动，供您参考与选择，您可随时让我把某个热点加入行程或移除。排名已经按热度排序。

如果您想调整行程的某个部分（比如改变某一天的活动，或者添加/删除景点），请告诉我！
"""

    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": plan_summary})
    state["messages"] = messages
    state["current_phase"] = "refining"

    return state


def node_refine_plan(state: TravelPlanState) -> TravelPlanState:
    """
    根据用户反馈调整行程
    """
    print("[Node] Refining travel plan...")

    messages = state.get("messages", [])

    # 提取用户最后的调整请求
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # 获取当前的行程和景点数据
    current_itinerary = state.get("itinerary", {})
    current_spots = state.get("featured_spots", [])
    destination = state.get("destination", "未知")
    days = state.get("days", 3)
    interests = state.get("interests", ["景点"])

    # 使用 GPT 分析用户的调整需求并生成新的行程
    system_prompt = f"""你是一个专业的旅行规划助手。用户已经看到了他们的行程计划，现在想要调整。

当前行程信息：
- 目的地：{destination}
- 天数：{days}天
- 兴趣：{", ".join(interests)}
- 当前行程有 {len(current_itinerary.get("plans", []))} 天的安排

用户的调整请求：{last_user_msg}

请分析用户想要如何调整（例如：改变某天的活动、添加/删除景点、调整时间安排等）。
然后以 JSON 格式返回调整后的完整行程计划，格式为：
{{
  "plans": [
    {{
      "id": "day_1",
      "day": "Day 1",
      "activities": [
        {{"id": "act_1_morning", "icon": "🗺️", "title": "活动名称", "time": "08:00 - 12:00", "description": "活动描述"}}
      ]
    }}
  ]
}}

如果用户只是询问或闲聊，返回 {{"no_change": true}}。
只返回 JSON，不要其他文字。"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": system_prompt}
            ]
        )

        response_text = response.choices[0].message.content
        print(f"[Node] Refine GPT Response: {response_text[:200]}...")

        # 尝试解析 JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))

            # 如果 GPT 表示不需要修改
            if parsed.get("no_change"):
                print("[Node] No itinerary change needed")
                assistant_message = "好的，我明白了。如果您需要调整行程的具体部分，请告诉我您想改变哪一天或哪个活动。"
            else:
                # 更新 state 中的 itinerary
                if "plans" in parsed:
                    state["itinerary"] = parsed
                    print(f"[Node] Updated itinerary with {len(parsed['plans'])} days")
                    assistant_message = "好的，我已经根据您的要求调整了行程计划。您可以在右侧看到更新后的行程安排。如果还需要进一步调整，请随时告诉我！"
                else:
                    assistant_message = "我理解了您的需求，但需要更具体的信息才能调整行程。请告诉我您想改变哪一天或哪个活动。"
        else:
            # JSON 解析失败，给出友好回复
            assistant_message = "我理解您想调整行程。请具体告诉我您想修改哪一天的安排，或者想添加/删除哪些景点，我会为您更新。"

    except Exception as e:
        print(f"[Node] Refine error: {e}")
        assistant_message = "抱歉，我在处理您的调整请求时遇到了问题。请再详细描述一下您想如何修改行程？"

    messages.append({"role": "assistant", "content": assistant_message})
    state["messages"] = messages

    return state


def extract_info_from_message(state: TravelPlanState, message: str) -> TravelPlanState:
    """
    从用户消息中提取信息
    """
    message_lower = message.lower()
    message_stripped = message.strip()

    # 检测目的地
    destinations = ["香港", "上海", "北京", "深圳", "杭州", "西安", "广州"]
    for dest in destinations:
        if dest in message:
            state["destination"] = dest
            break

    # 检测天数 - 改进：支持单独的数字（如"3"表示3天）
    days_match = re.search(r'(\d+)\s*天', message)
    if days_match:
        state["days"] = int(days_match.group(1))
    elif message_stripped.isdigit() and not state.get("days"):
        # 如果用户只回复了数字且还没有设置天数，假设是回答天数
        state["days"] = int(message_stripped)
        print(f"[Extract] Detected days from digit-only input: {state['days']}")

    # 检测人数
    people_match = re.search(r'(\d+)\s*(?:个)?(?:人|位)', message)
    if people_match:
        state["people_count"] = int(people_match.group(1))

    # 检测兴趣
    interests_keywords = {
        "美食": ["美食", "吃", "餐厅", "小吃"],
        "购物": ["购物", "逛街", "购买"],
        "景点": ["景点", "景观", "游览", "参观"],
        "文化": ["文化", "博物馆", "历史"],
        "户外": ["户外", "爬山", "登山", "自然"],
    }

    interests = state.get("interests", [])
    for interest, keywords in interests_keywords.items():
        for keyword in keywords:
            if keyword in message:
                if interest not in interests:
                    interests.append(interest)

    if interests:
        state["interests"] = interests

    # 检测预算 - 改进：支持单独的"低"、"中"、"高"回复
    if "预算" in message or "费用" in message or message_stripped in ["低", "中", "高"]:
        if "低" in message or message_stripped == "低":
            state["budget"] = "低"
        elif "高" in message or message_stripped == "高":
            state["budget"] = "高"
        else:
            state["budget"] = "中"

    return state


def should_generate_plan(state: TravelPlanState) -> bool:
    """
    判断是否收集了足够的信息可以生成行程
    """
    has_destination = bool(state.get("destination"))
    has_days = state.get("days", 0) > 0
    has_interests = len(state.get("interests", [])) > 0

    return has_destination and has_days and has_interests


# ====== 创建 Graph（目前主流程没用到，可留作后续扩展） ======

def create_travel_planning_agent():
    """
    创建旅行规划 Agent 的 LangGraph
    """
    workflow = StateGraph(TravelPlanState)

    # 添加节点
    workflow.add_node("greeting", node_greeting)
    workflow.add_node("gather_info", node_gather_info)
    workflow.add_node("generate_plan", node_generate_plan)
    workflow.add_node("refine_plan", node_refine_plan)

    # 添加边
    workflow.set_entry_point("greeting")
    workflow.add_edge("greeting", "gather_info")

    # 条件边：根据是否收集了足够信息决定是否生成计划
    workflow.add_conditional_edges(
        "gather_info",
        lambda x: "generate_plan" if x.get("info_complete") else "gather_info",
        {
            "generate_plan": "generate_plan",
            "gather_info": "gather_info"
        }
    )

    workflow.add_edge("generate_plan", "refine_plan")
    workflow.add_edge("refine_plan", "refine_plan")

    # 编译 Graph
    app = workflow.compile()
    return app


# ====== 运行 Agent 的函数 ======

def process_user_message(user_message: str, state: TravelPlanState) -> tuple[TravelPlanState, str, dict]:
    """
    处理用户消息，返回更新后的状态、AI回复和任何需要传递给前端的数据
    
    Returns:
        (updated_state, ai_response, frontend_updates)
    """
    print(f"[Agent] Processing user message: {user_message}")

    # 将用户消息添加到历史
    messages = state.get("messages", [])
    messages.append({"role": "user", "content": user_message})
    state["messages"] = messages

    # 根据当前阶段处理
    current_phase = state.get("current_phase", "greeting")

    if current_phase == "greeting":
        state = node_greeting(state)
    elif current_phase == "gathering_info":
        state = node_gather_info(state)
        # 关键点：如果在 gather_info 中已经把 info 补全，并把 current_phase 设成 generating_plan，
        # 在同一次请求里立刻生成行程，避免“慢一步”的问题
        if state.get("current_phase") == "generating_plan":
            state = node_generate_plan(state)
    elif current_phase == "generating_plan":
        state = node_generate_plan(state)
    elif current_phase == "refining":
        state = node_refine_plan(state)

    # 获取最新的 AI 响应
    ai_response = ""
    if state.get("messages"):
        last_msg = state["messages"][-1]
        if last_msg.get("role") == "assistant":
            ai_response = last_msg.get("content", "")

    # 准备前端更新数据
    frontend_updates = {}
    if state.get("itinerary"):
        frontend_updates["updateItinerary"] = state["itinerary"]["plans"]
    if state.get("featured_spots"):
        frontend_updates["updateFeaturedSpots"] = state["featured_spots"]
    if state.get("city_hotspots"):
        # 将热点转为 HotActivity 可用的简化结构
        frontend_updates["updateHotActivities"] = [
            {"id": h.get("id"), "title": f"{h.get('title')} (排名{h.get('rank')})", "link": "#", "hot": True}
            for h in state.get("city_hotspots", [])
        ]

    return state, ai_response, frontend_updates
