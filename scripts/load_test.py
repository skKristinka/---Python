"""Нагрузочный скрипт: N параллельных GET-запросов к серверу (скриншот S12).

Пример: python -m scripts.load_test http://localhost:8080/ -n 100
"""
import argparse
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from src.client.http_client import HttpClient
from src.http.exceptions import ParseError


def one_request(url: str, timeout: float) -> str:
    """Один запрос; результат — код статуса или имя исключения."""
    try:
        return str(HttpClient(timeout=timeout).get(url).status)
    except (ConnectionError, TimeoutError, ParseError) as exc:
        return type(exc).__name__


def run_load(url: str, total: int = 100, timeout: float = 5.0) -> Counter:
    """Отправить total запросов одновременно (по потоку на запрос)."""
    with ThreadPoolExecutor(max_workers=total) as pool:
        return Counter(pool.map(lambda _i: one_request(url, timeout), range(total)))


def main() -> int:
    """Запустить нагрузку и вывести итог; код выхода 0, если все ответы 200."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", nargs="?", default="http://localhost:8080/")
    parser.add_argument("-n", "--count", type=int, default=100, help="число запросов")
    parser.add_argument("-t", "--timeout", type=float, default=5.0, help="таймаут, с")
    args = parser.parse_args()
    started = time.perf_counter()
    results = run_load(args.url, args.count, args.timeout)
    elapsed = time.perf_counter() - started
    print(f"URL: {args.url}  запросов: {args.count}  время: {elapsed:.2f} с "
          f"({args.count / elapsed:.0f} запр/с)")
    for outcome, number in sorted(results.items()):
        print(f"  {outcome}: {number}")
    ok = results.get("200", 0) == args.count
    print("ВСЕ ОТВЕТЫ 200" if ok else "ЕСТЬ ОШИБКИ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
