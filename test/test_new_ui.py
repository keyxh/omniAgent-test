import requests
import json
import time

BASE_URL = "http://localhost:19901"

def test_api_health():
    print("=== 测试API健康状态 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/workers")
        print(f"员工API状态: {response.status_code}")
        if response.ok:
            workers = response.json()
            print(f"当前员工数: {len(workers)}")
            for w in workers:
                print(f"  - {w['name']} (ID: {w['id']}, 默认: {w['is_default']})")
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_cli_tools():
    print("=== 测试工具API ===")
    try:
        response = requests.get(f"{BASE_URL}/api/cli-tools")
        print(f"工具API状态: {response.status_code}")
        if response.ok:
            tools = response.json()
            print(f"当前工具数: {len(tools)}")
            for t in tools:
                print(f"  - {t['name']} (类别: {t.get('category', 'unknown')})")
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_create_worker():
    print("=== 测试创建员工 ===")
    worker_data = {
        "name": "代码审查员",
        "prompt": "专注于代码质量评估，识别潜在Bug和性能瓶颈，提供优化建议。",
        "model": "gpt-4",
        "provider": "openai"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/workers", json=worker_data)
        print(f"创建员工状态: {response.status_code}")
        if response.ok:
            worker = response.json()
            print(f"创建成功: {worker['name']} (ID: {worker['id']})")
            return worker['id']
        else:
            print(f"创建失败: {response.text}")
    except Exception as e:
        print(f"错误: {e}")
    print()
    return None

def test_curl_tool_available():
    print("=== 测试curl工具可用性 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/cli-tools")
        if response.ok:
            tools = response.json()
            curl_tool = next((t for t in tools if t['name'] == 'curl'), None)
            if curl_tool:
                print(f"curl工具已注册: {curl_tool['description']}")
                print(f"参数: {json.dumps(curl_tool['parameters'], indent=2, ensure_ascii=False)}")
            else:
                print("curl工具未找到")
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_multi_worker_chat():
    print("=== 测试多员工协作 ===")
    chat_data = {
        "message": "请帮我分析当前项目结构，并列出所有Python文件",
        "worker_id": "default"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json=chat_data, stream=True)
        print(f"聊天API状态: {response.status_code}")
        if response.ok:
            print("开始接收响应...")
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        data = decoded[6:]
                        if data == '[DONE]':
                            print("\n响应完成")
                            break
                        try:
                            msg = json.loads(data)
                            if msg.get('type') == 'content':
                                print(msg.get('content', ''), end='', flush=True)
                        except:
                            pass
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_delete_worker(worker_id):
    print(f"=== 测试删除员工 {worker_id} ===")
    try:
        response = requests.delete(f"{BASE_URL}/api/workers/{worker_id}")
        print(f"删除状态: {response.status_code}")
        if response.ok:
            print("删除成功")
        else:
            print(f"删除失败: {response.text}")
    except Exception as e:
        print(f"错误: {e}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("OmniAgent v002 测试脚本")
    print("=" * 60)
    print()
    
    test_api_health()
    test_cli_tools()
    test_curl_tool_available()
    
    new_worker_id = test_create_worker()
    
    if new_worker_id:
        time.sleep(1)
        test_api_health()
        time.sleep(1)
        test_delete_worker(new_worker_id)
        time.sleep(1)
        test_api_health()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)