import array
import hashlib
import math
import pickle
from typing import List


class BloomLayer:
    def __init__(self, n: int, target_error: float):
        """
        :param n: 预期元素数量
        :param target_error: 本层目标误差率
        """
        # 计算布隆参数
        self.counter_bits = 8
        self.max_count = 2**self.counter_bits - 1
        self.m = self._calculate_capacity(n, target_error)
        self.k = self._optimal_hashes(self.m, n)
        self.counters = array.array("B", [0]) * self.m
        self.element_count = 0

    def _optimal_hashes(self, m: int, n: int) -> int:
        # 计算哈希函数数量 k = (m / n) * ln2
        return math.ceil((m / n) * math.log(2))

    def _calculate_capacity(self, n: int, p: float) -> int:
        # 计算位数组大小 m = -n * ln(p) / (ln2)^2
        return math.ceil(-n * math.log(p) / (math.log(2) ** 2))

    def _set_counter(self, idx: int, value: int):
        """安全设置计数器值"""
        self.counters[idx] = max(0, min(value, self.max_count))

    def load_factor(self) -> float:
        return self.element_count / (self.m / self.k)

    def update(self, indices: List[int], delta: int):
        """更新计数器"""
        for idx in indices:
            current = self.counters[idx]
            self._set_counter(idx, current + delta)
        self.element_count += delta

    def check(self, indices: List[int]) -> bool:
        return all(self.counters[idx] > 0 for idx in indices)


class CoutingBloomFilter:
    """分层计数布隆过滤器"""

    def __init__(self, max_error=0.001, initial_elements=100000):
        self.max_error = max_error
        self.layers: List[BloomLayer] = []
        self.remaining_error = max_error
        self._add_layer(initial_elements, max_error)

    def _add_layer(self, n: int, layer_error: float):
        new_layer = BloomLayer(n, layer_error)
        self.layers.append(new_layer)
        self.remaining_error -= layer_error

    def _hash(self, element: bytes, layer: BloomLayer) -> List[int]:
        """哈希函数"""
        hash_full = hashlib.sha1(element).digest()
        hash1 = int.from_bytes(hash_full[:4], byteorder="big")
        hash2 = int.from_bytes(hash_full[4:8], byteorder="big")
        return [(hash1 + i * hash2) % layer.m for i in range(layer.k)]

    def add(self, element):
        element_bytes = self._to_bytes(element)
        indices = self._hash(element_bytes, self.layers[-1])
        self.layers[-1].update(indices, 1)

    def __contains__(self, element) -> bool:
        element_bytes = self._to_bytes(element)
        for layer in reversed(self.layers):
            indices = self._hash(element_bytes, layer)
            if layer.check(indices):
                return True
        return False

    def remove(self, element):
        element_bytes = self._to_bytes(element)
        for layer in reversed(self.layers):
            indices = self._hash(element_bytes, layer)
            if layer.check(indices):
                layer.update(indices, -1)
                return
        raise ValueError("Element not found")

    def _to_bytes(self, element):
        # 将元素转换为字节
        if isinstance(element, bytes):
            return element
        elif isinstance(element, str):
            return element.encode("utf-8")
        else:
            return pickle.dumps(element)


class ScalableCoutingBloomFilter(CoutingBloomFilter):
    """计数布隆过滤器"""

    def __init__(self, max_error=0.001, initial_elements=200000):
        self.max_error = max_error
        self.layers: List[BloomLayer] = []
        self.remaining_error = max_error
        self._add_layer(initial_elements, max_error / 2)

    def add(self, element):
        current_layer = self.layers[-1]

        # 自动扩容逻辑
        if current_layer.load_factor() > 0.75:
            new_error = self.remaining_error * 0.5
            new_n = current_layer.element_count * 2
            self._add_layer(new_n, new_error)
        element_bytes = self._to_bytes(element)
        indices = self._hash(element_bytes, self.layers[-1])
        self.layers[-1].update(indices, 1)
