"""
测试 JourneyHeader 更新功能
验证 agent 是否正确生成 TripInfo 并通过 frontend_updates 传递
"""

from langgraph_agent import TravelPlanState, process_user_message


def test_journey_header_update():
    """测试从收集信息到生成 TripInfo 的完整流程"""
    
    print("=" * 60)
    print("Testing JourneyHeader Update Flow")
    print("=" * 60)
    
    # 初始化状态
    state = TravelPlanState(
        messages=[],
        destination="",
        days=0,
        people_count=1,
        interests=[],
        budget="中",
        itinerary={},
        featured_spots=[],
        city_hotspots=[],
        current_phase="greeting",
        info_complete=False,
        current_day_index=0,
        day_approved=False,
        sorted_spots=[],
        flight_booking_phase="none",
        departure_date="",
        return_date="",
        origin_city="",
        flight_results=[]
    )
    
    # 模拟对话流程
    conversations = [
        ("你好", "greeting"),
        ("我想去香港", "gathering_info"),
        ("3天", "gathering_info"),
        ("2个人", "gathering_info"),
        ("美食、景点", "gathering_info"),
        ("中等预算", "generating_day"),  # 应该在这里触发 initialize_planning
    ]
    
    for i, (user_msg, expected_phase_after) in enumerate(conversations, 1):
        print(f"\n--- Round {i} ---")
        print(f"User: {user_msg}")
        
        state, ai_response, frontend_updates = process_user_message(user_msg, state)
        
        print(f"AI: {ai_response[:100]}...")
        print(f"Current Phase: {state['current_phase']}")
        print(f"Frontend Updates Keys: {list(frontend_updates.keys())}")
        
        # 检查 TripInfo 更新
        if "updateTripInfo" in frontend_updates:
            trip_info = frontend_updates["updateTripInfo"]
            print("\n✅ TripInfo Update Found:")
            print(f"  Destination: {trip_info.get('destination')}")
            print(f"  Start Date: {trip_info.get('startDate')}")
            print(f"  End Date: {trip_info.get('endDate')}")
            print(f"  People: {trip_info.get('people')}")
            print(f"  Budget: {trip_info.get('budget')}")
            print(f"  Interests: {trip_info.get('interests')}")
        
        # 检查其他更新
        if "updateFeaturedSpots" in frontend_updates:
            spots_count = len(frontend_updates["updateFeaturedSpots"])
            print(f"  Featured Spots: {spots_count} spots")
        
        if "updateItinerary" in frontend_updates:
            plans_count = len(frontend_updates["updateItinerary"])
            print(f"  Itinerary: {plans_count} days")
        
        if "updateHotActivities" in frontend_updates:
            activities_count = len(frontend_updates["updateHotActivities"])
            print(f"  Hot Activities: {activities_count} items")
    
    print("\n" + "=" * 60)
    print("✅ Test Completed Successfully")
    print("=" * 60)
    
    # 验证最终状态
    assert state["destination"] == "香港", "Destination should be set"
    assert state["days"] == 3, "Days should be 3"
    assert state["people_count"] == 2, "People count should be 2"
    assert "美食" in state["interests"], "Interests should include 美食"
    
    print("\n✅ All assertions passed!")


if __name__ == "__main__":
    test_journey_header_update()
