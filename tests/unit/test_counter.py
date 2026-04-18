"""Counter 类的单元测试"""

import sys
from pathlib import Path
import threading

# 将 agent 目录加入 sys.path 以便导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "agent"))

from utils.counter import Counter


class TestCounterBasic:
    """基础功能测试"""

    def test_increment_new_key(self):
        c = Counter()
        c.increment("task_1")
        assert c.get_count("task_1") == 1

    def test_increment_existing_key(self):
        c = Counter()
        c.increment("task_1")
        c.increment("task_1")
        assert c.get_count("task_1") == 2

    def test_increment_custom_amount(self):
        c = Counter()
        c.increment("task_1", amount=5)
        assert c.get_count("task_1") == 5

    def test_get_count_missing_key(self):
        c = Counter()
        assert c.get_count("nonexistent") == 0

    def test_reset_specific_key(self):
        c = Counter()
        c.increment("task_1", amount=10)
        c.increment("task_2", amount=20)
        c.reset("task_1")
        assert c.get_count("task_1") == 0
        assert c.get_count("task_2") == 20

    def test_reset_all(self):
        c = Counter()
        c.increment("task_1")
        c.increment("task_2")
        c.reset()
        assert c.get_count("task_1") == 0
        assert c.get_count("task_2") == 0

    def test_reset_nonexistent_key_no_error(self):
        c = Counter()
        c.reset("nonexistent")  # should not raise

    def test_multiple_keys_independent(self):
        c = Counter()
        c.increment("a")
        c.increment("b", amount=3)
        c.increment("a")
        assert c.get_count("a") == 2
        assert c.get_count("b") == 3


class TestCounterThreadSafety:
    """线程安全测试"""

    def test_concurrent_increments(self):
        c = Counter()
        num_threads = 10
        increments_per_thread = 1000

        def worker():
            for _ in range(increments_per_thread):
                c.increment("shared")

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert c.get_count("shared") == num_threads * increments_per_thread

    def test_concurrent_increment_and_reset(self):
        c = Counter()

        def incrementer():
            for _ in range(500):
                c.increment("key")

        def resetter():
            for _ in range(100):
                c.reset("key")

        t1 = threading.Thread(target=incrementer)
        t2 = threading.Thread(target=resetter)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        # Just verify no crash; final value is nondeterministic
        assert isinstance(c.get_count("key"), int)
