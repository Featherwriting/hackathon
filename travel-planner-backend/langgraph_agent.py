"""
LangGraph-based Travel Planning Agent
智能旅行规划 Agent，能够逐步询问用户需求并生成动态行程计划
"""

from typing import TypedDict, Annotated, Sequence
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


# ====== 初始化 OpenAI Client ======
client = OpenAI()
MODEL_NAME = "gpt-4o-mini"  # 或使用 "gpt-3.5-turbo" 以降低成本

# ====== 工具定义 ======
# TODO: 这里的生成行程是纯扯淡，让LLM介入思考一个合理安排的，不一定每天时间要占满
def generate_itinerary(destination: str, days: int, interests: list[str], budget: str, featured_spots: list[dict] | None = None) -> dict:
    """
    根据用户需求生成行程计划。可选地将 `featured_spots` 嵌入到每日活动中。

    返回: {"plans": [ {id, day, activities:[{id,title,time,description,ref_spot_id?}] }]}
    """
    print(f"[Tool] Generating itinerary: {destination}, {days} days, interests: {interests}, budget: {budget}, spots={len(featured_spots) if featured_spots else 0}")

    activities_templates = {
        "morning": ["景点游览", "博物馆参观", "寺庙祈福", "早茶体验", "街头漫步"],
        "afternoon": ["购物逛街", "特色餐厅", "下午茶", "文化体验", "休闲娱乐"],
        "evening": ["晚餐享受", "夜景观赏", "酒吧小坐", "演艺表演", "夜间游览"],
    }

    icons_map = {
        "景点游览": "🗺️",
        "博物馆参访": "🏛️",
        "寺庙祈福": "🏮",
        "早茶体验": "☕",
        "街头漫步": "🚶",
        "购物逛街": "🛍️",
        "特色餐厅": "🍽️",
        "下午茶": "🫖",
        "文化体验": "🎭",
        "休闲娱乐": "🎪",
        "晚餐享受": "🍽️",
        "夜景观赏": "🌉",
        "酒吧小坐": "🍹",
        "演艺表演": "🎬",
        "夜间游览": "🌙",
    }

    plans = []
    base_times = {
        "morning": ("08:00", "12:00"),
        "afternoon": ("13:00", "17:00"),
        "evening": ("19:00", "22:00"),
    }

    # 平均分配景点到每个时间段（如果有提供）
    spots_queue = list(featured_spots) if featured_spots else []

    for day_idx in range(days):
        day_activities = []

        for period in ["morning", "afternoon", "evening"]:
            start_time, end_time = base_times[period]

            # 如果有可用的景点，优先使用景点填充活动
            if spots_queue:
                spot = spots_queue.pop(0)
                title = spot.get("title", f"{destination} 景点")
                description = spot.get("description", spot.get("category", "热门景点"))
                activity = {
                    "id": f"act_{day_idx + 1}_{period}",
                    "icon": "🗺️",
                    "title": title,
                    "time": f"{start_time} - {end_time}",
                    "description": description,
                    "ref_spot_id": spot.get("id")
                }
            else:
                # 回退到模板活动
                activity_name = activities_templates[period][day_idx % len(activities_templates[period])]
                activity = {
                    "id": f"act_{day_idx + 1}_{period}",
                    "icon": icons_map.get(activity_name, "📍"),
                    "title": f"{destination} {activity_name}",
                    "time": f"{start_time} - {end_time}",
                    "description": f"体验{destination}的{activity_name}，尽享当地风情。"
                }

            day_activities.append(activity)

        plans.append({
            "id": f"day_{day_idx + 1}",
            "day": f"Day {day_idx + 1}",
            "activities": day_activities
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


# 已改为使用独立的 search_tool.search_city_hotspots，实现更完善的检索 + 评分 + JSON 结构。



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
        # 添加一个简短的过渡消息，然后让 process_user_message 调用 node_generate_plan
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
    system_prompt = """你是一个专业的旅行规划助手。你已经收集了用户的需求，现在要为他们生成一份行程计划总结。

请用友好的语气告诉用户：
1. 他们的旅行地点、天数、人数
2. 你已经为他们准备的行程概览
3. 推荐的景点
4. 问他们是否满意，或者是否需要调整某些部分

中文回复，保持热情和专业。"""
    
    destination = state.get("destination", "未知")
    days = state.get("days", 0)
    people = state.get("people_count", 1)
    interests = ",".join(state.get("interests", [])) or "多样化"
    
    plan_summary = f"""
我已经为您准备好了完整的行程计划！

目的地：{destination}
天数：{days}天
人数：{people}人
兴趣：{interests}

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
                    assistant_message = f"好的，我已经根据您的要求调整了行程计划。您可以在右侧看到更新后的行程安排。如果还需要进一步调整，请随时告诉我！"
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


# ====== 创建 Graph ======

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
        # 检查在 gather_info 后是否应该生成计划
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
