#!/usr/bin/env python3
"""Summarize recorded EPS recovery JSONL events without contacting a vehicle."""

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize_log(path):
    events = Counter()
    outcomes = Counter()
    failures = []
    probes = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f'{path}:{line_number}: invalid JSON') from exc
        kind = record.get('event')
        detail = record.get('detail', {})
        if not isinstance(detail, dict):
            detail = {}
        events[kind] += 1
        if kind == 'probe':
            result = detail.get('nrc') or detail.get('tag') or 'no NRC recorded'
            if detail.get('accepted') is True:
                result = 'accepted'
            outcomes[str(result)] += 1
            probes.append((line_number, detail.get('addr'), detail.get('size'), result))
        elif kind in {'security_access', 'session_control', 'f100', 'erase', 'f101'}:
            if detail.get('success') is False:
                failures.append((line_number, kind, detail.get('error', 'failed')))
    return events, outcomes, probes, failures


def summarize_state(path):
    state = json.loads(path.read_text())
    probes = state.get('probes', [])
    return Counter(item.get('result', 'unknown') for item in probes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', nargs='*', type=Path, help='Original recovery JSONL logs')
    parser.add_argument('--state', type=Path, help='Optional saved scan state JSON')
    parser.add_argument('--show-probes', action='store_true')
    args = parser.parse_args()
    if not args.logs and not args.state:
        parser.error('provide at least one log or --state')
    for path in args.logs:
        events, outcomes, probes, failures = summarize_log(path)
        print(f'{path}: {sum(events.values())} events, {len(probes)} download probes')
        print('  Probe outcomes:', dict(outcomes))
        print('  Preparation failures:', len(failures))
        if args.show_probes:
            for line, address, size, result in probes:
                print(f'  line {line}: {address} + {size}: {result}')
            for line, kind, error in failures:
                print(f'  line {line}: {kind}: {error}')
    if args.state:
        print(f'{args.state}: saved probe results {dict(summarize_state(args.state))}')
        print('A preparation failure in saved state is not a rejected download request.')


if __name__ == '__main__':
    main()
