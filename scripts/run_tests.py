"""从任意仓库目录名运行现有业务测试，不访问真实平台账号。"""

from pathlib import Path

import importlib.util
import argparse
import concurrent.futures
import json
import subprocess
import sys
import tempfile
import time
import unittest


class TimedResult(unittest.TextTestResult):
    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        self.timings.append((time.perf_counter() - self.started, test.id()))
        super().stopTest(test)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []


def tests(group):
    for test in group:
        if isinstance(test, unittest.TestSuite):
            yield from tests(test)
        else:
            yield test


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, choices=(1, 2), default=1)
    parser.add_argument('--modules', nargs='+', help=argparse.SUPPRESS)
    parser.add_argument('--report', help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    name = "local_bilibili_autopilot"
    spec = importlib.util.spec_from_file_location(name, root / "__init__.py",
                                                submodule_search_locations=[str(root)])
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载插件测试包")
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    cases = list(tests(suite))
    discovered = {test.id() for test in cases}
    for group in ['test_autopilot', 'test_client_plugin', 'test_recovery', 'test_replies', 'test_sharing', 'test_webui', 'test_handoff', 'test_candidates', 'test_ecosystem', 'test_activity', 'test_login_diagnostics', 'test_journal', 'test_cover', 'test_transport', 'test_platform_scope', 'test_reading_diagnostics']:
        if not any(test.startswith(group + '.') for test in discovered):
            raise RuntimeError('Missing required test group: ' + group)
    if args.workers == 2 and not args.modules:
        # Whole modules preserve module/class fixtures; every process has its own
        # interpreter, asyncio loops and original per-test on-disk databases.
        modules = {name.split('.')[0] for name in discovered}
        shards = [[], []]
        sizes = [0, 0]
        for module in sorted(modules, key=lambda m: (-sum(n.startswith(m + '.') for n in discovered), m)):
            index = sizes.index(min(sizes))
            shards[index].append(module)
            sizes[index] += sum(n.startswith(module + '.') for n in discovered)
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix='bili-test-reports-') as directory:
            def run(index):
                report = Path(directory) / f'{index}.json'
                result = subprocess.run(
                    [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                     '--modules', *shards[index], '--report', str(report)],
                    cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace',
                    timeout=900,
                )
                return result, json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(run, range(2)))
            executed = []
            failed = False
            for index, (outcome, report) in enumerate(outcomes):
                print(f'Worker {index + 1}:', ', '.join(shards[index]), flush=True)
                print(outcome.stdout, end='')
                print(outcome.stderr, end='', file=sys.stderr)
                expected = {n for n in discovered if n.split('.')[0] in shards[index]}
                actual = report.get('ids', [])
                executed.extend(actual)
                failed |= (outcome.returncode != 0 or set(actual) != expected
                           or report.get('tests_run') != len(expected) or report.get('skipped') != 0)
            failed |= len(executed) != len(discovered) or set(executed) != discovered
            print(f'Aggregate: {len(executed)}/{len(discovered)} tests, '
                  f'{time.perf_counter() - started:.3f}s wall, success={not failed}', flush=True)
            return int(failed)
    if args.modules:
        cases = [test for test in cases if test.id().split('.')[0] in args.modules]
        suite = unittest.TestSuite(cases)
    executed = [test.id() for test in cases]
    result = unittest.TextTestRunner(verbosity=2, resultclass=TimedResult).run(suite)
    print('Slowest tests (including setup, teardown and cleanup):', flush=True)
    for seconds, name in sorted(result.timings, reverse=True)[:20]:
        print(f'{seconds:.3f}s {name}', flush=True)
    if args.report:
        Path(args.report).write_text(json.dumps({'ids': executed, 'tests_run': result.testsRun,
                                              'skipped': len(result.skipped)}), encoding='utf-8')
    return 0 if result.testsRun and result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
