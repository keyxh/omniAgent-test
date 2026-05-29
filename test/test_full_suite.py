import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:19901"
test_results = []

def log_test(test_name, status, details=""):
    result = {
        "name": test_name,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} {test_name}: {status}")
    if details:
        print(f"   详情: {details}")

def test_api_health():
    """测试API健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("API健康检查", "PASS", f"状态: {data['status']}, 版本: {data['version']}")
            return True
        else:
            log_test("API健康检查", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("API健康检查", "FAIL", str(e))
        return False

def test_workers_list():
    """测试获取员工列表"""
    try:
        response = requests.get(f"{BASE_URL}/api/workers", timeout=5)
        if response.status_code == 200:
            workers = response.json()
            log_test("获取员工列表", "PASS", f"共 {len(workers)} 个员工")
            for w in workers:
                print(f"   - {w.get('name', 'Unknown')} (ID: {w.get('id', 'N/A')})")
            return workers
        else:
            log_test("获取员工列表", "FAIL", f"HTTP {response.status_code}")
            return []
    except Exception as e:
        log_test("获取员工列表", "FAIL", str(e))
        return []

def test_create_worker_valid():
    """测试创建有效员工"""
    worker_data = {
        "name": "代码审查员",
        "prompt": "专注于代码质量评估，识别潜在Bug和性能瓶颈，提供优化建议。",
        "model": "gpt-4",
        "provider": "openai"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/workers",
            json=worker_data,
            timeout=5
        )
        
        if response.status_code == 200:
            worker = response.json()
            log_test("创建有效员工", "PASS", f"ID: {worker.get('id')}, 名称: {worker.get('name')}")
            return worker.get('id')
        else:
            log_test("创建有效员工", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("创建有效员工", "FAIL", str(e))
        return None

def test_create_worker_missing_name():
    """测试缺少名称的员工创建"""
    worker_data = {
        "prompt": "这是一个没有名称的员工"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/workers",
            json=worker_data,
            timeout=5
        )
        
        if response.status_code == 422:
            log_test("创建无名称员工（预期失败）", "PASS", "正确拒绝无效请求")
            return True
        else:
            log_test("创建无名称员工（预期失败）", "FAIL", f"应返回422，实际返回{response.status_code}")
            return False
    except Exception as e:
        log_test("创建无名称员工（预期失败）", "FAIL", str(e))
        return False

def test_create_worker_missing_prompt():
    """测试缺少提示词的员工创建"""
    worker_data = {
        "name": "测试员工"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/workers",
            json=worker_data,
            timeout=5
        )
        
        if response.status_code == 422:
            log_test("创建无提示词员工（预期失败）", "PASS", "正确拒绝无效请求")
            return True
        else:
            log_test("创建无提示词员工（预期失败）", "FAIL", f"应返回422，实际返回{response.status_code}")
            return False
    except Exception as e:
        log_test("创建无提示词员工（预期失败）", "FAIL", str(e))
        return False

def test_create_worker_empty():
    """测试空数据创建员工"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/workers",
            json={},
            timeout=5
        )
        
        if response.status_code == 422:
            log_test("创建空数据员工（预期失败）", "PASS", "正确拒绝空请求")
            return True
        else:
            log_test("创建空数据员工（预期失败）", "FAIL", f"应返回422，实际返回{response.status_code}")
            return False
    except Exception as e:
        log_test("创建空数据员工（预期失败）", "FAIL", str(e))
        return False

def test_get_single_worker(worker_id):
    """测试获取单个员工详情"""
    if not worker_id:
        log_test("获取单个员工详情", "SKIP", "无可用员工ID")
        return None
    
    try:
        response = requests.get(f"{BASE_URL}/api/workers/{worker_id}", timeout=5)
        
        if response.status_code == 200:
            worker = response.json()
            log_test("获取单个员工详情", "PASS", f"名称: {worker.get('name')}, ID: {worker.get('id')}")
            return worker
        else:
            log_test("获取单个员工详情", "FAIL", f"HTTP {response.status_code}")
            return None
    except Exception as e:
        log_test("获取单个员工详情", "FAIL", str(e))
        return None

def test_delete_worker(worker_id):
    """测试删除员工"""
    if not worker_id:
        log_test("删除员工", "SKIP", "无可用员工ID")
        return False
    
    try:
        response = requests.delete(f"{BASE_URL}/api/workers/{worker_id}", timeout=5)
        
        if response.status_code == 200:
            log_test("删除员工", "PASS", f"成功删除员工 {worker_id}")
            return True
        else:
            log_test("删除员工", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("删除员工", "FAIL", str(e))
        return False

def test_cli_tools():
    """测试工具列表API"""
    try:
        response = requests.get(f"{BASE_URL}/api/cli-tools", timeout=5)
        
        if response.status_code == 200:
            tools = response.json()
            categories = {}
            for tool in tools:
                cat = tool.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            log_test("获取工具列表", "PASS", f"共 {len(tools)} 个工具, 分类: {categories}")
            
            curl_tool = next((t for t in tools if t['name'] == 'curl'), None)
            if curl_tool:
                log_test("curl工具注册验证", "PASS", f"类别: {curl_tool.get('category')}")
            else:
                log_test("curl工具注册验证", "FAIL", "未找到curl工具")
            
            shell_tool = next((t for t in tools if t['name'] == 'shell'), None)
            if shell_tool:
                log_test("shell工具注册验证", "PASS", f"类别: {shell_tool.get('category')}")
            else:
                log_test("shell工具注册验证", "FAIL", "未找到shell工具")
            
            return tools
        else:
            log_test("获取工具列表", "FAIL", f"HTTP {response.status_code}")
            return []
    except Exception as e:
        log_test("获取工具列表", "FAIL", str(e))
        return []

def test_conversations_api():
    """测试对话API"""
    try:
        response = requests.get(f"{BASE_URL}/api/conversations", timeout=5)
        
        if response.status_code == 200:
            conversations = response.json()
            log_test("对话列表API", "PASS", f"共 {len(conversations)} 个对话")
            return True
        else:
            log_test("对话列表API", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("对话列表API", "FAIL", str(e))
        return False

def test_frontend_pages():
    """测试前端页面可访问性"""
    pages = [
        ("/", "首页"),
        ("/workers.html", "员工管理"),
        ("/cli-tools.html", "工具管理"),
        ("/settings.html", "设置页面")
    ]
    
    for path, name in pages:
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                log_test(f"前端页面 - {name}", "PASS", f"大小: {len(response.content)} bytes")
            else:
                log_test(f"前端页面 - {name}", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            log_test(f"前端页面 - {name}", "FAIL", str(e))

def test_cdn_resources_localization():
    """测试CDN资源本地化"""
    import os
    
    resources = [
        ("frontend/assets/tailwind-cdn.js", "Tailwind CSS"),
        ("frontend/assets/material-symbols-outlined.css", "Material Symbols CSS"),
        ("frontend/assets/inter-google.css", "Inter 字体 CSS"),
        ("frontend/assets/fonts/MaterialSymbolsOutlined-Regular.ttf", "Material Symbols 字体"),
        ("frontend/assets/fonts/Inter-Regular.ttf", "Inter Regular 字体"),
        ("frontend/assets/fonts/Inter-Medium.ttf", "Inter Medium 字体"),
        ("frontend/assets/fonts/Inter-SemiBold.ttf", "Inter SemiBold 字体"),
        ("frontend/assets/fonts/Inter-Bold.ttf", "Inter Bold 字体")
    ]
    
    base_path = Path(__file__).parent.parent
    
    for rel_path, name in resources:
        full_path = base_path / rel_path
        if full_path.exists():
            size = full_path.stat().st_size
            log_test(f"CDN资源本地化 - {name}", "PASS", f"存在，大小: {size} bytes")
        else:
            log_test(f"CDN资源本地化 - {name}", "FAIL", "文件不存在")

if __name__ == "__main__":
    print("=" * 70)
    print("OmniAgent v0.02 完整测试套件")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    if not test_api_health():
        print("\n❌ API服务不可用，终止测试")
        exit(1)
    
    print("\n--- 基础功能测试 ---\n")
    test_conversations_api()
    workers_before = test_workers_list()
    tools = test_cli_tools()
    
    print("\n--- 员工管理测试 ---\n")
    new_worker_id = test_create_worker_valid()
    test_create_worker_missing_name()
    test_create_worker_missing_prompt()
    test_create_worker_empty()
    
    if new_worker_id:
        time.sleep(0.5)
        test_get_single_worker(new_worker_id)
        time.sleep(0.5)
        test_delete_worker(new_worker_id)
    
    time.sleep(0.5)
    workers_after = test_workers_list()
    
    print("\n--- 前端和资源测试 ---\n")
    test_frontend_pages()
    test_cdn_resources_localization()
    
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in test_results if r["status"] == "SKIP")
    total = len(test_results)
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"跳过: {skipped} ⚠️")
    print(f"通过率: {(passed/total*100) if total > 0 else 0:.1f}%")
    
    if failed > 0:
        print("\n❌ 失败的测试:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"   - {r['name']}: {r['details']}")
    
    print("\n" + "=" * 70)
    
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": (passed/total*100) if total > 0 else 0
            },
            "results": test_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 测试结果已保存到: {results_file}")
    
    exit(0 if failed == 0 else 1)