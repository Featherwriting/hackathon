"""
航班搜索工具
使用 Amadeus API 搜索航班信息
"""

import os
import re
import httpx
from typing import Optional

# 尝试导入 Amadeus SDK（可选）
try:
    from amadeus import Client
except ImportError:
    Client = None


def _parse_price_numeric(price_str: str) -> Optional[float]:
    """
    从价格字符串中提取数值
    例如: "¥1200", "$500", "1200 CNY" -> 1200.0
    """
    if not price_str:
        return None
    # 移除货币符号和字母，只保留数字和小数点
    cleaned = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_duration_minutes(duration_str: str) -> Optional[int]:
    """
    从时长字符串中提取分钟数
    例如: "PT2H30M" -> 150, "2h 30m" -> 150
    """
    if not duration_str:
        return None
    
    total_minutes = 0
    
    # ISO 8601 格式: PT2H30M
    iso_match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration_str)
    if iso_match:
        hours = int(iso_match.group(1) or 0)
        minutes = int(iso_match.group(2) or 0)
        return hours * 60 + minutes
    
    # 普通格式: "2h 30m" 或 "2小时30分钟"
    hours_match = re.search(r'(\d+)[hH小时]', duration_str)
    minutes_match = re.search(r'(\d+)[mM分钟]', duration_str)
    
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
    
    return total_minutes if total_minutes > 0 else None


def choose_best_flight(flights: list[dict]) -> Optional[dict]:
    """
    基于价格或时长简单选择最优航班（价格优先）
    
    Args:
        flights: 航班列表
    
    Returns:
        最优航班字典，如果列表为空则返回 None
    """
    if not flights:
        return None
    
    best = None
    best_score = None
    
    for f in flights:
        score = None
        
        # 优先按价格排序
        price = _parse_price_numeric(f.get('price') or f.get('fare') or '')
        if price is not None:
            score = price
        else:
            # 如果没有价格，按时长排序
            duration = _parse_duration_minutes(f.get('duration') or '')
            if duration is not None:
                score = duration / 60.0  # 转换为小时
        
        # 如果既没有价格也没有时长，给一个很大的分数（最差）
        if score is None:
            score = 1e9
        
        if best is None or score < best_score:
            best = f
            best_score = score
    
    return best


def search_flights(
    origin: str,
    destination: str,
    departure_date: Optional[str] = None,
    adults: int = 1,
    max_results: int = 3
) -> dict:
    """
    调用 Amadeus API 搜索航班，返回结构 {"flights": [...]}
    
    Args:
        origin: 出发地（城市名或 IATA 代码）
        destination: 目的地（城市名或 IATA 代码）
        departure_date: 出发日期，格式 YYYY-MM-DD（可选）
        adults: 成人数量，默认 1
        max_results: 最多返回结果数，默认 3
    
    Returns:
        包含航班列表的字典: {"flights": [...]}
    """
    api_key = os.getenv("AMADEUS_API_KEY")
    api_secret = os.getenv("AMADEUS_API_SECRET")
    
    if not api_key or not api_secret:
        print("[Flight Search] Amadeus credentials missing; skipping flight search")
        return {"flights": []}

    def resolve_iata(name: str) -> Optional[str]:
        """
        将城市名转换为 IATA 代码
        支持常见中国城市的本地映射，其他城市通过 API 查询
        """
        if not name:
            return None
        
        code = name.strip()
        
        # 如果已经是 3 字母 IATA 代码，直接返回
        if re.fullmatch(r"[A-Za-z]{3}", code):
            return code.upper()
        
        # 常见中国城市映射
        local_mapping = {
            "北京": "PEK",
            "上海": "PVG",
            "广州": "CAN",
            "深圳": "SZX",
            "杭州": "HGH",
            "西安": "XIY",
            "香港": "HKG",
            "成都": "CTU",
            "重庆": "CKG",
            "南京": "NKG",
            "武汉": "WUH",
            "厦门": "XMN",
            "青岛": "TAO",
            "大连": "DLC",
            "天津": "TSN",
        }
        
        if code in local_mapping:
            return local_mapping[code]
        
        # 通过 Amadeus API 查询 IATA 代码
        try:
            token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
            token_response = httpx.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_key,
                    "client_secret": api_secret
                },
                timeout=8.0
            )
            
            if token_response.status_code != 200:
                return None
            
            token = token_response.json().get("access_token")
            if not token:
                return None
            
            headers = {"Authorization": f"Bearer {token}"}
            loc_url = "https://test.api.amadeus.com/v1/reference-data/locations"
            
            location_response = httpx.get(
                loc_url,
                params={
                    "subType": "CITY",
                    "keyword": code,
                    "page[limit]": 1
                },
                headers=headers,
                timeout=8.0
            )
            
            if location_response.status_code != 200:
                return None
            
            data = location_response.json().get("data", [])
            if not data:
                return None
            
            entry = data[0]
            iata = entry.get("iataCode") or entry.get("id")
            
            if iata and isinstance(iata, str) and len(iata) >= 3:
                return iata[:3].upper()
                
        except Exception as e:
            print(f"[Flight Search] Error resolving IATA code for {code}: {e}")
            return None
        
        return None

    # 解析出发地和目的地的 IATA 代码
    origin_iata = resolve_iata(origin) or origin
    dest_iata = resolve_iata(destination) or destination

    print(f"[Flight Search] Searching flights: {origin_iata} -> {dest_iata}")

    # 构建请求参数
    params = {
        "originLocationCode": origin_iata,
        "destinationLocationCode": dest_iata,
        "adults": adults,
        "max": max_results
    }
    
    if departure_date:
        params["departureDate"] = departure_date

    flights = []

    # 优先尝试使用 Amadeus SDK
    if Client:
        try:
            client = Client(client_id=api_key, client_secret=api_secret)
            
            # 尝试不同的 API 端点
            resp = None
            try:
                resp = client.shopping.flight_offers.get(**params)
            except Exception:
                try:
                    resp = client.shopping.flight_offers_search.get(**params)
                except Exception:
                    pass
            
            if resp is not None:
                data = getattr(resp, 'data', [])
                
                for offer in data[:max_results]:
                    price = offer.get('price', {}).get('total') or ''
                    itineraries = offer.get('itineraries', [])
                    
                    if not itineraries:
                        continue
                    
                    first_itinerary = itineraries[0]
                    segments = first_itinerary.get('segments', [])
                    
                    if not segments:
                        continue
                    
                    first_seg = segments[0]
                    last_seg = segments[-1]
                    
                    dep = first_seg.get('departure', {})
                    arr = last_seg.get('arrival', {})
                    
                    flights.append({
                        'id': f"flight_{len(flights)+1}",
                        'origin': dep.get('iataCode') if isinstance(dep, dict) else origin_iata,
                        'destination': arr.get('iataCode') if isinstance(arr, dict) else dest_iata,
                        'departure': dep.get('at') if isinstance(dep, dict) else '',
                        'arrival': arr.get('at') if isinstance(arr, dict) else '',
                        'airline': first_seg.get('carrierCode') or '',
                        'flight_number': first_seg.get('number') or '',
                        'duration': first_itinerary.get('duration') or '',
                        'price': price,
                    })
                    
        except Exception as e:
            print(f"[Flight Search] Amadeus SDK error: {e}")
            flights = []
    
    # 如果 SDK 失败或没有结果，可以添加 HTTP 回退逻辑
    if not flights:
        print("[Flight Search] No flights found via SDK, consider adding HTTP fallback")
        # 这里可以添加直接 HTTP 请求的备用方案
    
    print(f"[Flight Search] Found {len(flights)} flights")
    return {"flights": flights}


if __name__ == "__main__":
    # 测试代码
    result = search_flights(
        origin="北京",
        destination="上海",
        departure_date="2025-12-01",
        adults=1,
        max_results=3
    )
    
    print(f"\n找到 {len(result['flights'])} 个航班:")
    for flight in result['flights']:
        print(f"\n航班 {flight['id']}:")
        print(f"  {flight['origin']} -> {flight['destination']}")
        print(f"  出发: {flight['departure']}")
        print(f"  到达: {flight['arrival']}")
        print(f"  航空公司: {flight['airline']} {flight['flight_number']}")
        print(f"  时长: {flight['duration']}")
        print(f"  价格: {flight['price']}")
    
    if result['flights']:
        best = choose_best_flight(result['flights'])
        print(f"\n最优航班: {best['id']} (价格: {best['price']})")
