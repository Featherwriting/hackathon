# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# 开发环境直接全放开 CORS，所有来源都可以访问 /api/*
CORS(app)

# ====== 内存“数据库” ======
chats = {}              # sessionId -> list of messages
itineraries = {}        # itineraryId -> dict
drafts = {}             # (userId, itineraryId) -> draft
exports = {}            # itineraryId -> downloadUrl
shares = {}             # itineraryId -> shareUrl
itinerary_progress = {} # itineraryId -> {"progressPercent":..,"statusCode":..}


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


# 健康检查
@app.route("/api/health", methods=["GET"])
def health_check():
    return {"status": "ok"}


# 1. AI 聊天 /api/ai/chat
@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    data = request.get_json(force=True)

    session_id = data["sessionId"]
    user_id = data["userId"]
    message_text = data["messageText"]

    chats.setdefault(session_id, []).append(
        {"userId": user_id, "text": message_text}
    )

    reply_text = f"你说的是：“{message_text}”，这是一个很不错的想法！"

    suggested_quick_actions = [
        "机票查询",
        "目的地推荐",
        "预算规划",
        "热门景点"
    ]

    return jsonify({
        "sessionId": session_id,
        "replyText": reply_text,
        "suggestedQuickActions": suggested_quick_actions
    })


# 2. 设置行程基础信息 /api/itinerary/base-info
@app.route("/api/itinerary/base-info", methods=["POST"])
def set_base_itinerary_info():
    data = request.get_json(force=True)

    user_id = data["userId"]
    itinerary_id = data.get("itineraryId") or gen_id("trip")
    city_name = data["cityName"]
    city_code = data.get("cityCode", "")
    start_date = data["startDate"]
    end_date = data["endDate"]
    traveler_count = data["travelerCount"]

    itineraries.setdefault(itinerary_id, {})
    itineraries[itinerary_id].update({
        "userId": user_id,
        "cityName": city_name,
        "cityCode": city_code,
        "startDate": start_date,
        "endDate": end_date,
        "travelerCount": traveler_count,
    })

    same_city_count = sum(
        it.get("travelerCount", 0)
        for it in itineraries.values()
        if it.get("cityName") == city_name
    )

    return jsonify({
        "itineraryId": itinerary_id,
        "sameCityTravelerCount": same_city_count
    })


# 3. 搜索旅友 /api/travelmate/search
@app.route("/api/travelmate/search", methods=["POST"])
def search_travelmates():
    data = request.get_json(force=True)

    city_name = data["cityName"]
    page_number = data.get("pageNumber", 1)
    page_size = data.get("pageSize", 10)

    demo_items = [
        {
            "mateId": f"mate_{i}",
            "nickname": f"{city_name}玩家{i}",
            "avatarUrl": "https://example.com/avatar.png",
            "tags": data.get("tags", ["Citywalk", "摄影"])
        }
        for i in range(1, 21)
    ]

    total_count = len(demo_items)
    start = (page_number - 1) * page_size
    end = start + page_size
    items = demo_items[start:end]

    return jsonify({
        "totalCount": total_count,
        "items": items
    })


# 4. 活动列表 /api/activity/list
@app.route("/api/activity/list", methods=["POST"])
def list_activities():
    data = request.get_json(force=True)

    city_name = data["cityName"]
    page_number = data.get("pageNumber", 1)
    page_size = data.get("pageSize", 10)

    demo_activities = [
        {
            "activityId": f"act_{i}",
            "title": f"{city_name} 活动 {i}",
            "summary": "这是一个很不错的活动",
            "priceAmount": 199 + i,
            "imageUrl": "https://example.com/activity.png"
        }
        for i in range(1, 31)
    ]

    total_count = len(demo_activities)
    start = (page_number - 1) * page_size
    end = start + page_size
    items = demo_activities[start:end]

    return jsonify({
        "totalCount": total_count,
        "items": items
    })


# 5. POI 列表 /api/poi/list
@app.route("/api/poi/list", methods=["POST"])
def list_pois():
    data = request.get_json(force=True)

    city_name = data["cityName"]
    category_code = data["categoryCode"]
    page_number = data.get("pageNumber", 1)
    page_size = data.get("pageSize", 10)

    demo_pois = [
        {
            "poiId": f"{category_code}_{i}",
            "poiName": f"{city_name}景点 {i}",
            "coverImageUrl": "https://example.com/poi.png",
            "ratingScore": 4.0 + (i % 10) / 10,
            "priceAmount": 50 + i,
            "shortDescription": f"{city_name} 的打卡地 {i}"
        }
        for i in range(1, 41)
    ]

    total_count = len(demo_pois)
    start = (page_number - 1) * page_size
    end = start + page_size
    items = demo_pois[start:end]

    return jsonify({
        "totalCount": total_count,
        "items": items
    })


# 6. 将 POI 加入行程 /api/itinerary/poi/add
@app.route("/api/itinerary/poi/add", methods=["POST"])
def add_poi_to_itinerary():
    data = request.get_json(force=True)

    itinerary_id = data["itineraryId"]
    day_index = data["dayIndex"]
    time_slot_code = data["timeSlotCode"]
    poi_id = data["poiId"]
    expected_duration_hours = data.get("expectedDurationHours")
    expected_cost_amount = data.get("expectedCostAmount")

    itinerary = itineraries.setdefault(itinerary_id, {})
    days = itinerary.setdefault("days", [])

    while len(days) < day_index:
        days.append({"dayIndex": len(days) + 1, "segments": []})

    day = days[day_index - 1]
    segment_id = gen_id("seg")

    detail = {
        "poiId": poi_id,
        "timeSlotCode": time_slot_code,
        "expectedDurationHours": expected_duration_hours,
        "expectedCostAmount": expected_cost_amount
    }

    day["segments"].append({
        "segmentId": segment_id,
        "segmentTypeCode": "poi",
        "title": f"游玩 {poi_id}",
        "startTime": "09:00",
        "endTime": "12:00",
        "detail": detail
    })

    return jsonify({"success": True})


# 7. 生成行程 /api/itinerary/generate
@app.route("/api/itinerary/generate", methods=["POST"])
def generate_itinerary():
    data = request.get_json(force=True)

    user_id = data["userId"]
    itinerary_id = data.get("itineraryId") or gen_id("trip")
    city_name = data["cityName"]
    city_code = data.get("cityCode", "")
    start_date = data.get("startDate", "")
    end_date = data.get("endDate", "")
    traveler_count = data["travelerCount"]
    budget_amount = data.get("budgetAmount")

    # 校验日期
    if not start_date or not end_date:
        return jsonify({
            "error": "startDate and endDate are required in format YYYY-MM-DD"
        }), 400

    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
    except ValueError:
        return jsonify({
            "error": f"Invalid date format. Got startDate={start_date}, endDate={end_date}, expected YYYY-MM-DD"
        }), 400

    days_count = (end - start).days + 1
    if days_count <= 0:
        return jsonify({
            "error": "endDate must be >= startDate"
        }), 400

    days = []
    for i in range(days_count):
        current_date = start + timedelta(days=i)
        day_index = i + 1
        segments = [
            {
                "segmentId": gen_id("seg"),
                "segmentTypeCode": "poi",
                "title": f"{city_name} 打卡景点 {day_index}",
                "startTime": "10:00",
                "endTime": "12:00",
                "detail": {}
            },
            {
                "segmentId": gen_id("seg"),
                "segmentTypeCode": "food",
                "title": f"{city_name} 美食推荐 {day_index}",
                "startTime": "12:30",
                "endTime": "14:00",
                "detail": {}
            },
        ]
        days.append({
            "dayIndex": day_index,
            "date": current_date.strftime("%Y-%m-%d"),
            "segments": segments
        })

    itineraries[itinerary_id] = {
        "userId": user_id,
        "cityName": city_name,
        "cityCode": city_code,
        "startDate": start_date,
        "endDate": end_date,
        "travelerCount": traveler_count,
        "budgetAmount": budget_amount,
        "days": days,
    }

    itinerary_progress[itinerary_id] = {
        "progressPercent": 100,
        "statusCode": "finished"
    }

    return jsonify({
        "itineraryId": itinerary_id,
        "days": days,
        "progressPercent": 100
    })


# 8. 替换行程段 /api/itinerary/segment/replace
@app.route("/api/itinerary/segment/replace", methods=["POST"])
def replace_itinerary_segment():
    data = request.get_json(force=True)

    itinerary_id = data["itineraryId"]
    day_index = data["dayIndex"]
    segment_id = data["segmentId"]

    itinerary = itineraries.get(itinerary_id)
    if not itinerary:
        return jsonify({"success": False}), 404

    days = itinerary.get("days", [])
    if day_index < 1 or day_index > len(days):
        return jsonify({"success": False}), 404

    day = days[day_index - 1]
    segments = day.get("segments", [])

    replaced = False
    for idx, seg in enumerate(segments):
        if seg["segmentId"] == segment_id:
            segments[idx] = {
                "segmentId": gen_id("seg"),
                "segmentTypeCode": "poi",
                "title": "替换后的景点",
                "startTime": seg.get("startTime", "10:00"),
                "endTime": seg.get("endTime", "12:00"),
                "detail": {}
            }
            replaced = True
            break

    return jsonify({"success": replaced})


# 9. 社交 Feed /api/social/feed
@app.route("/api/social/feed", methods=["POST"])
def social_feed():
    data = request.get_json(force=True)

    city_name = data["cityName"]
    page_number = data.get("pageNumber", 1)
    page_size = data.get("pageSize", 10)

    demo_posts = [
        {
            "postId": f"post_{i}",
            "title": f"{city_name} 旅行日记 {i}",
            "coverImageUrl": "https://example.com/post.png",
            "authorName": f"游客{i}"
        }
        for i in range(1, 51)
    ]

    total_count = len(demo_posts)
    start = (page_number - 1) * page_size
    end = start + page_size
    items = demo_posts[start:end]

    return jsonify({
        "totalCount": total_count,
        "items": items
    })


# 10. Web 搜索 /api/search/web
@app.route("/api/search/web", methods=["POST"])
def web_search():
    data = request.get_json(force=True)

    query_text = data["queryText"]
    items = [
        {
            "title": f"关于 {query_text} 的旅游攻略",
            "url": "https://example.com/search-result",
            "snippet": "这里是搜索结果摘要..."
        }
    ]

    return jsonify({"items": items})


# 11. 保存草稿 /api/itinerary/save-draft
@app.route("/api/itinerary/save-draft", methods=["POST"])
def save_draft():
    data = request.get_json(force=True)

    user_id = data["userId"]
    itinerary_id = data["itineraryId"]
    title = data["title"]
    itinerary_data = data["itineraryData"]

    drafts[(user_id, itinerary_id)] = {
        "title": title,
        "itineraryData": itinerary_data
    }

    return jsonify({"success": True})


# 12. 导出行程 /api/itinerary/export
@app.route("/api/itinerary/export", methods=["POST"])
def export_itinerary():
    data = request.get_json(force=True)

    itinerary_id = data["itineraryId"]
    export_format_code = data["exportFormatCode"]

    download_url = f"https://example.com/download/{itinerary_id}.{export_format_code}"
    exports[itinerary_id] = download_url

    return jsonify({"downloadUrl": download_url})


# 13. 分享行程 /api/itinerary/share
@app.route("/api/itinerary/share", methods=["POST"])
def share_itinerary():
    data = request.get_json(force=True)

    itinerary_id = data["itineraryId"]
    share_type_code = data["shareTypeCode"]

    share_url = f"https://example.com/share/{itinerary_id}"
    shares[itinerary_id] = share_url

    return jsonify({"shareUrl": share_url})


# 14. 获取行程进度 /api/itinerary/progress
@app.route("/api/itinerary/progress", methods=["POST"])
def get_itinerary_progress():
    data = request.get_json(force=True)

    itinerary_id = data["itineraryId"]
    info = itinerary_progress.get(itinerary_id, {
        "progressPercent": 0,
        "statusCode": "generating"
    })

    return jsonify({
        "itineraryId": itinerary_id,
        "progressPercent": info["progressPercent"],
        "statusCode": info["statusCode"]
    })


if __name__ == "__main__":
    # 开发模式直接运行
    app.run(host="0.0.0.0", port=5000, debug=True)
