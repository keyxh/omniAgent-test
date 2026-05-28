#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 测试脚本
测试提供的 API 是否可用
"""

import requests
import json

API_URL = "http://wenhui.ifast.fgct.cc/v1/chat/completions"
MODEL = "GLM-4.7-flash-UD-IQ1_S.gguf"

def test_api():
    """测试 API 连接"""
    
    print(f"测试 API: {API_URL}")
    print(f"模型: {MODEL}")
    print("-" * 50)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "你好，请回复'测试成功'"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        print("发送请求...")
        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 连接成功!")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
                print(f"\n模型回复: {content}")
                return True
        else:
            print(f"❌ API 返回错误: {response.status_code}")
            print(f"错误内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_api_with_key(api_key=None):
    """测试带 API Key 的连接"""
    
    print(f"\n测试带 API Key 的连接...")
    print("-" * 50)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "temperature": 0.7,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 连接成功!")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
            return True
        else:
            print(f"响应: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("OmniAgent API 测试")
    print("=" * 50)
    
    success = test_api()
    
    if not success:
        print("\n尝试不带 v1 路径...")
        API_URL_ALT = "http://wenhui.ifast.fgct.cc/chat/completions"
        
        headers = {"Content-Type": "application/json"}
        data = {
            "model": MODEL,
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 50
        }
        
        try:
            response = requests.post(API_URL_ALT, headers=headers, json=data, timeout=30)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:500]}")
        except Exception as e:
            print(f"错误: {e}")