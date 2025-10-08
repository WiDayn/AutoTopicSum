"""API测试脚本"""
import requests
import json
import time

BASE_URL = "http://localhost:5001/api"


def test_health():
    """测试健康检查接口"""
    print("\n=== 测试健康检查接口 ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")


def test_search(query):
    """测试搜索接口"""
    print(f"\n=== 测试搜索接口: '{query}' ===")
    params = {
        'query': query,
        'language': 'zh-CN',
        'region': 'CN',
        'limit': 10
    }
    
    print(f"请求参数: {params}")
    print("正在搜索...")
    
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/events/search", params=params)
    elapsed_time = time.time() - start_time
    
    print(f"耗时: {elapsed_time:.2f}秒")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"成功: {data.get('success')}")
        print(f"消息: {data.get('message')}")
        
        if data.get('success') and data.get('data'):
            event = data['data'].get('event', {})
            articles = data['data'].get('articles', [])
            
            print(f"\n事件ID: {event.get('id')}")
            print(f"事件标题: {event.get('title')}")
            print(f"来源数量: {event.get('source_count')}")
            print(f"聚合文章数: {len(articles)}")
            
            print(f"\n前3篇文章:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n{i}. {article.get('title')}")
                print(f"   来源: {article.get('source')}")
                print(f"   时间: {article.get('published_at')}")
                print(f"   链接: {article.get('url')}")
    else:
        print(f"错误响应: {response.text}")


def test_get_events():
    """测试获取事件列表接口"""
    print("\n=== 测试获取事件列表接口 ===")
    response = requests.get(f"{BASE_URL}/events")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        events = data.get('data', {}).get('events', [])
        print(f"事件总数: {len(events)}")
        
        if events:
            print("\n事件列表:")
            for event in events:
                print(f"- [{event.get('id')}] {event.get('title')} ({event.get('source_count')} 个来源)")


def test_get_event_detail(event_id):
    """测试获取事件详情接口"""
    print(f"\n=== 测试获取事件详情接口: {event_id} ===")
    response = requests.get(f"{BASE_URL}/events/{event_id}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            event = data.get('data', {})
            print(f"事件标题: {event.get('title')}")
            print(f"事件摘要: {event.get('summary')[:100]}...")
            print(f"来源数量: {len(event.get('sources', []))}")
    else:
        print(f"错误响应: {response.text}")


def main():
    """主函数"""
    print("=" * 60)
    print("新闻聚合引擎 API 测试")
    print("=" * 60)
    
    try:
        # 1. 测试健康检查
        test_health()
        
        # 2. 测试搜索功能
        test_queries = ["人工智能", "气候变化"]
        for query in test_queries:
            test_search(query)
            time.sleep(2)  # 避免请求过快
        
        # 3. 测试获取事件列表
        time.sleep(1)
        test_get_events()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n错误: 无法连接到后端服务")
        print("请确保后端服务已启动在 http://localhost:5001")
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")


if __name__ == "__main__":
    main()

