#!/usr/bin/env python3
"""
ClashRuleProvider 插件修复验证脚本

用于测试修复后的功能是否正常工作
"""

import sys
import json
import requests
from typing import Optional


class ClashRuleProviderTester:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def test_health_check(self) -> bool:
        """测试健康检查接口"""
        print("\n=== 测试健康检查接口 ===")
        url = f"{self.base_url}/api/v1/plugin/clashruleprovider/health"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 健康检查成功")
                print(f"  - 总体状态: {data.get('data', {}).get('overall_status', 'unknown')}")
                print(f"  - 数据完整性: {data.get('data', {}).get('data_integrity', False)}")
                print(f"  - 缓存状态: {data.get('data', {}).get('cache_status', 'unknown')}")
                print(f"  - 订阅数: {data.get('data', {}).get('subscriptions_count', 0)}")
                print(f"  - 代理数: {data.get('data', {}).get('proxies_count', 0)}")
                print(f"  - 规则数: {data.get('data', {}).get('rules_count', 0)}")
                return True
            else:
                print(f"✗ 健康检查失败: HTTP {response.status_code}")
                print(f"  响应: {response.text}")
                return False
        except Exception as e:
            print(f"✗ 健康检查异常: {e}")
            return False

    def test_cache_clear(self) -> bool:
        """测试清除缓存接口"""
        print("\n=== 测试清除缓存接口 ===")
        url = f"{self.base_url}/api/v1/plugin/clashruleprovider/health/cache-clear"
        try:
            response = requests.post(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 清除缓存成功: {data.get('message', '')}")
                return True
            else:
                print(f"✗ 清除缓存失败: HTTP {response.status_code}")
                print(f"  响应: {response.text}")
                return False
        except Exception as e:
            print(f"✗ 清除缓存异常: {e}")
            return False

    def test_plugin_status(self) -> bool:
        """测试插件状态接口"""
        print("\n=== 测试插件状态接口 ===")
        url = f"{self.base_url}/api/v1/plugin/clashruleprovider/status"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 插件状态获取成功")
                print(f"  - 启用状态: {data.get('data', {}).get('state', False)}")
                return True
            else:
                print(f"✗ 插件状态获取失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 插件状态获取异常: {e}")
            return False

    def test_proxies_list(self) -> bool:
        """测试代理列表接口"""
        print("\n=== 测试代理列表接口 ===")
        url = f"{self.base_url}/api/v1/plugin/clashruleprovider/proxies"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                proxies = data.get('data', [])
                print(f"✓ 代理列表获取成功: {len(proxies)} 个代理")
                return True
            else:
                print(f"✗ 代理列表获取失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 代理列表获取异常: {e}")
            return False

    def test_rule_providers(self) -> bool:
        """测试规则提供者接口"""
        print("\n=== 测试规则提供者接口 ===")
        url = f"{self.base_url}/api/v1/plugin/clashruleprovider/rule-providers"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                providers = data.get('data', [])
                print(f"✓ 规则提供者获取成功: {len(providers)} 个提供者")
                return True
            else:
                print(f"✗ 规则提供者获取失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 规则提供者获取异常: {e}")
            return False

    def run_all_tests(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("ClashRuleProvider 插件修复验证测试")
        print("=" * 60)

        results = {
            'health_check': self.test_health_check(),
            'cache_clear': self.test_cache_clear(),
            'plugin_status': self.test_plugin_status(),
            'proxies_list': self.test_proxies_list(),
            'rule_providers': self.test_rule_providers()
        }

        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{test_name}: {status}")

        print("\n" + "=" * 60)
        print(f"总计: {passed}/{total} 测试通过")
        print("=" * 60)

        if passed == total:
            print("\n🎉 所有测试通过!插件修复成功!")
        else:
            print("\n⚠️  部分测试失败,请检查日志获取详细信息")

        return results


def main():
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python test_fix.py <MoviePilot_URL> <API_Token>")
        print("\n示例:")
        print("  python test_fix.py http://localhost:3000 your-api-token-here")
        sys.exit(1)

    base_url = sys.argv[1]
    api_token = sys.argv[2]

    tester = ClashRuleProviderTester(base_url, api_token)
    results = tester.run_all_tests()

    # 返回退出码
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
