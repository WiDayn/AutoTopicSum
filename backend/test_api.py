"""API测试脚本"""
import requests
import json
import time
import pprint

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


def run_e2e_test(single_test_query):
    if not single_test_query:
        print('!!! 错误: 请检查single_test_query')
        return

    poll_interval_secs = 3  # 每3秒轮询一次
    task_timeout_secs = 300  # 超时时间

    print(f'--- 步骤 1: 提交搜索任务: "{single_test_query}" ---')
    try:
        response = requests.post(
            f'{BASE_URL}/events/search',
            json={'query': single_test_query}
        )
        response.raise_for_status()  
        
        submit_data = response.json()
        
        if not submit_data.get('success'):
            print(f'!!! 错误: 提交任务失败: {submit_data.get("message")}')
            return

        task_id = submit_data.get('data', {}).get('task_id')
        event_id = submit_data.get('data', {}).get('event_id')

        if not task_id or not event_id:
            print('!!! 错误: 提交响应中未找到 task_id 或 event_id')
            return
            
        print(f'任务已成功提交。')
        print(f'  Task ID:  {task_id}')
        print(f'  Event ID: {event_id}')

    except requests.exceptions.ConnectionError:
        print(f'!!! 错误: 无法连接到 {BASE_URL}')
        return
    except requests.exceptions.RequestException as e:
        print(f'!!! 错误: 提交任务时发生异常: {e}')
        return

    print(f'\n--- 步骤 2: 轮询任务状态 (每 {poll_interval_secs} 秒一次) ---')
    start_time = time.time()

    while True:
        # 检查是否超时
        if time.time() - start_time > task_timeout_secs:
            print(f'!!! 错误: 任务超时 (超过 {task_timeout_secs} 秒)')
            return

        try:
            task_response = requests.get(f'{BASE_URL}/tasks/{task_id}')
            task_data = task_response.json()

            if not task_data.get('success'):
                print(f'警告: 获取任务状态失败: {task_data.get("message")}, 3秒后重试...')
                time.sleep(poll_interval_secs)
                continue
            
            status = task_data.get('data', {}).get('status')
            progress = task_data.get('data', {}).get('progress', {})
            message = progress.get('message', '...')
            
            if status == 'completed':
                print('任务完成! ')
                break
            elif status == 'failed':
                print(f'!!! 错误: 任务执行失败! 详情: {task_data.get("data", {}).get("error")}')
                return
            else: 
                # 状态为 processing 或 submitted
                current = progress.get('current', 0)
                total = progress.get('total', 100)
                percent = (current / total) * 100 if total > 0 else 0
                print(f'状态: {status} ({percent:.0f}%) - {message}')
                time.sleep(poll_interval_secs)
        
        except requests.exceptions.RequestException as e:
            print(f'轮询时出错: {e}, 3秒后重试...')
            time.sleep(poll_interval_secs)

    print(f'\n--- 步骤 3: 获取最终事件详情 (Event ID: {event_id}) ---')
    try:
        event_response = requests.get(f'{BASE_URL}/events/{event_id}')
        event_response.raise_for_status()
        event_data_wrapper = event_response.json()

        if not event_data_wrapper.get('success'):
            print(f'!!! 错误: 获取事件详情失败: {event_data_wrapper.get("message")}')
            return
        
        event_data = event_data_wrapper.get('data', {})
        
        print('成功获取事件，详情如下:')
        pprint.pp(event_data, depth=2, compact=True)

        print('\n--- 步骤 4: 验证 Timeline 结果 ---')

        if 'timeline' not in event_data:
            print('\n!!! 失败: timeline 字段不存在于最终的 event 数据中!')
            print('请检查 _create_event_from_articles 和 _handle_search_task 方法。')
        
        elif not isinstance(event_data['timeline'], list):
            print(f'\n!!! 失败: timeline 字段不是一个列表 (List), 而是 {type(event_data["timeline"])}')
        
        elif len(event_data['timeline']) == 0:
            print('\n--- 注意: timeline 字段是一个空列表 []')

        else:
            timeline_len = len(event_data['timeline'])
            print(f'\n=== 成功! timeline 字段已成功生成! ===')
            print(f'    共包含 {timeline_len} 个关键事件节点。')
            print('    第一个节点示例:')
            pprint.pp(event_data['timeline'][0], depth=2, compact=True)

    except requests.exceptions.RequestException as e:
        print(f'!!! 错误: 获取最终事件时发生异常: {e}')


def main():
    """主函数"""
    print("=" * 60)
    print("新闻聚合引擎 API 测试")
    print("=" * 60)
    
    try:
        # 1. 测试健康检查
        test_health()
        
        # 2. 测试搜索功能
        # test_queries = ["人工智能", "气候变化"]
        # for query in test_queries:
        #     test_search(query)
        #     time.sleep(2)  # 避免请求过快
        run_e2e_test('人工智能')
        
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
