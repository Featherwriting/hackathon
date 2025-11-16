"""
测试机票预订 Agent 功能
"""

from langgraph_agent import TravelPlanState, process_user_message

def test_flight_booking():
    """测试完整的机票预订流程"""
    
    # 初始化状态
    state: TravelPlanState = {
        "messages": [],
        "destination": "",
        "days": 0,
        "people_count": 0,
        "interests": [],
        "budget": "",
        "itinerary": {},
        "featured_spots": [],
        "city_hotspots": [],
        "current_phase": "greeting",
        "info_complete": False,
        "current_day_index": 0,
        "day_approved": False,
        "sorted_spots": [],
        "flight_booking_phase": "none",
        "departure_date": "",
        "return_date": "",
        "origin_city": "",
        "flight_results": [],
    }
    
    print("=" * 60)
    print("机票预订 Agent 测试")
    print("=" * 60)
    
    # 模拟对话流程
    test_messages = [
        "你好",
        "我想去香港玩",
        "3天",
        "2人",
        "美食、景点",
        "中等预算",
        "满意了",  # Day 1
        "满意了",  # Day 2
        "满意了",  # Day 3 - 此时进入 completed 阶段
        "我想预订机票",  # 触发机票预订
        "从北京出发，12月1日",  # 提供出发城市和日期
    ]
    
    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"回合 {i}")
        print(f"{'='*60}")
        print(f"👤 用户: {user_msg}")
        
        state, ai_response, frontend_updates = process_user_message(user_msg, state)
        
        print(f"\n🤖 助手: {ai_response}")
        print(f"\n📊 当前阶段: {state.get('current_phase')}")
        
        if state.get("flight_booking_phase") != "none":
            print(f"✈️ 机票预订阶段: {state.get('flight_booking_phase')}")
        
        if frontend_updates:
            print(f"\n📤 前端更新:")
            for key, value in frontend_updates.items():
                if isinstance(value, list):
                    print(f"  - {key}: {len(value)} 项")
                else:
                    print(f"  - {key}: {value}")
        
        # 如果到达机票搜索阶段，显示结果
        if state.get("flight_results"):
            results = state["flight_results"]
            print(f"\n✈️ 航班搜索结果:")
            
            if results.get("best_outbound"):
                flight = results["best_outbound"]
                print(f"  去程: {flight.get('airline')} {flight.get('flight_number')}")
                print(f"    出发: {flight.get('departure')}")
                print(f"    到达: {flight.get('arrival')}")
                print(f"    价格: {flight.get('price')}")
            
            if results.get("best_return"):
                flight = results["best_return"]
                print(f"  返程: {flight.get('airline')} {flight.get('flight_number')}")
                print(f"    出发: {flight.get('departure')}")
                print(f"    到达: {flight.get('arrival')}")
                print(f"    价格: {flight.get('price')}")
    
    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")
    
    # 打印最终状态
    print("\n📋 最终状态摘要:")
    print(f"  目的地: {state.get('destination')}")
    print(f"  天数: {state.get('days')}")
    print(f"  出发城市: {state.get('origin_city')}")
    print(f"  出发日期: {state.get('departure_date')}")
    print(f"  返回日期: {state.get('return_date')}")
    print(f"  当前阶段: {state.get('current_phase')}")
    print(f"  机票预订阶段: {state.get('flight_booking_phase')}")


if __name__ == "__main__":
    test_flight_booking()
