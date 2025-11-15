"""
CopilotKit FastAPI Remote Endpoint for Travel Planner
使用 CopilotKit 官方 SDK 和 LangGraph Agent
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import json
import httpx
from urllib.parse import quote
from langgraph_agent import TravelPlanState, process_user_message

# ====== 初始化 FastAPI 应用 ======
app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== 内存会话存储（生产环境应使用数据库） ======
sessions = {}


def get_or_create_session(thread_id: str) -> TravelPlanState:
    """
    获取或创建用户会话
    """
    if thread_id not in sessions:
        sessions[thread_id] = TravelPlanState(
            messages=[],
            destination="",
            days=0,
            people_count=1,
            interests=[],
            budget="中",
            itinerary={},
            featured_spots=[],
            current_phase="greeting",
            info_complete=False
        )
    return sessions[thread_id]


# ====== 主聊天端点 ======

@app.post("/copilotkit_remote")
async def copilotkit_chat_handler(request: Request):
    """
    CopilotKit 聊天处理程序
    集成 LangGraph Agent 进行智能旅行规划
    """
    try:
        # 获取请求数据
        body = await request.body()
        data = json.loads(body)
        
        print(f"[Request] Received request: {json.dumps(data, ensure_ascii=False)[:200]}...")
        
        # 提取请求信息 (更健壮地处理 messages 结构)
        variables = data.get('variables', {})
        req_data = variables.get('data', {})
        messages = req_data.get('messages', []) or []
        thread_id = req_data.get('threadId', '') or ''

        # 获取用户最后一条消息 — 支持多种消息结构
        user_message = ''
        for msg in reversed(messages):
            # 优先处理常见的 textMessage 格式
            text_msg = msg.get('textMessage') if isinstance(msg, dict) else None
            if isinstance(text_msg, dict):
                if text_msg.get('role') == 'user' and text_msg.get('content'):
                    user_message = text_msg.get('content', '')
                    break

            # 其次支持直接的 content 或 message.body 等变体
            if isinstance(msg, dict):
                # common fallbacks
                if msg.get('role') == 'user' and msg.get('content'):
                    user_message = msg.get('content')
                    break
                if msg.get('text') and isinstance(msg.get('text'), str):
                    user_message = msg.get('text')
                    break
                # nested input structure
                nested = msg.get('input') or msg.get('message')
                if isinstance(nested, dict) and nested.get('text'):
                    user_message = nested.get('text')
                    break
        
        print(f"[Chat] User message: {user_message}")
        print(f"[Chat] Thread ID: {thread_id}")
        
        # 获取或创建用户会话
        session_state = get_or_create_session(thread_id)
        
        print(f"[Session] Loaded state: destination={session_state.get('destination')}, days={session_state.get('days')}, interests={session_state.get('interests')}")
        
        # 处理用户消息并获取 AI 响应
        updated_state, ai_response, frontend_updates = process_user_message(
            user_message,
            session_state
        )
        
        # 更新会话
        sessions[thread_id] = updated_state
        
        print(f"[Session] Saved state: destination={updated_state.get('destination')}, days={updated_state.get('days')}, interests={updated_state.get('interests')}")
        print(f"[Chat] AI Response: {ai_response[:100]}...")
        print(f"[Chat] Frontend Updates: {list(frontend_updates.keys())}")
        
        # 如果没有 thread_id，生成一个（避免前端/测试缺少 threadId 导致的问题）
        if not thread_id:
            thread_id = f"thread-{uuid.uuid4().hex[:8]}"

        # 若 AI 未生成回复，使用友好默认文本，避免返回空 content 导致前端异常
        if not ai_response:
            ai_response = "抱歉，我暂时无法生成回复，请重试或稍后再试。"
        
        # 构建 CopilotKit 格式的响应
        response = {
            "data": {
                "generateCopilotResponse": {
                    "threadId": thread_id,
                    "runId": f"run-{uuid.uuid4().hex[:8]}",
                    "status": {
                        "__typename": "BaseResponseStatus",
                        "code": "success"
                    },
                    "messages": [
                        {
                            "__typename": "TextMessageOutput",
                            "id": f"msg-{uuid.uuid4().hex[:8]}",
                            "role": "assistant",
                            "content": [ai_response],  # 必须是数组格式
                            "createdAt": datetime.now().isoformat(),
                            "status": {
                                "__typename": "SuccessMessageStatus",
                                "code": "success"
                            }
                        }
                    ],
                    "metaEvents": [],
                    # 如果有前端更新，通过 extensions 传递给前端
                    "extensions": {
                        "frontendActions": frontend_updates
                    }
                }
            }
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        print(f"[Error] {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse({
            "errors": [
                {
                    "message": f"Internal server error: {str(e)}",
                    "extensions": {
                        "code": "INTERNAL_SERVER_ERROR"
                    }
                }
            ]
        }, status_code=500)


# ====== 健康检查端点 ======

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Travel Planner Backend is running"}


@app.get("/api/bili_search")
async def bili_search(keyword: str, limit: int = 3):
    """后端代理 B 站搜索，打印详细调试信息到服务器终端（CMD/PowerShell）。

    返回格式：{"videos": [{id,title,pic,link,playCount}, ...]}
    """
    try:
        if not keyword:
            return JSONResponse({"videos": []})
        url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={quote(keyword)}&type=1&pn=1&ps={limit}"
        print(f"[bili_proxy] Requesting Bilibili API URL: {url}")
        # 使用浏览器风格的请求头尝试绕过简单的反爬检测
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            print(f"[bili_proxy] HTTP status: {resp.status_code} {resp.reason_phrase}")
            text_snippet = resp.text[:2000]
            print(f"[bili_proxy] Raw response snippet: {text_snippet}")
            if resp.status_code != 200:
                # 返回错误信息，前端可据此显示友好提示
                return JSONResponse({"videos": [], "error": {"status": resp.status_code, "snippet": text_snippet[:800]}}, status_code=200)
            j = resp.json()

        # 尝试解析常见字段
        candidates = []
        if isinstance(j, dict):
            data = j.get("data") or {}
            candidates = data.get("result") or data.get("vlist") or []

        videos = []
        for it in (candidates or []):
            bvid = it.get("bvid") or it.get("id") or (str(it.get("aid")) if it.get("aid") else None)
            title = it.get("title") or it.get("name") or ""
            # 去标签
            try:
                import re
                title = re.sub(r"<[^>]+>", "", title)
            except Exception:
                pass
            pic = it.get("pic") or it.get("cover") or ""
            stat = it.get("stat") or {}
            play = stat.get("view") or stat.get("play") or it.get("play") or it.get("playCount") or 0
            link = f"https://www.bilibili.com/video/{bvid}" if bvid else (it.get("url") or "")
            videos.append({"id": str(bvid or ""), "title": title, "pic": pic, "link": link, "playCount": int(play or 0)})

        videos = sorted(videos, key=lambda x: x.get("playCount", 0), reverse=True)[:limit]
        print(f"[bili_proxy] Parsed videos: {videos}")
        return JSONResponse({"videos": videos})
    except Exception as e:
        print(f"[bili_proxy] Error: {e}")
        return JSONResponse({"videos": []})


def main():
    """运行 Uvicorn 服务器"""
    print("=" * 60)
    print("Starting Travel Planner Backend with LangGraph Agent")
    print("=" * 60)
    print(f"Server running at: http://localhost:8000")
    print(f"CopilotKit Endpoint: http://localhost:8000/copilotkit_remote")
    print(f"Health Check: http://localhost:8000/api/health")
    print("=" * 60)
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
