"""Render the short research report from completed, audited evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = ROOT/'outputs/pilot-v1'
    audit = json.loads((run/'audit.json').read_text())
    if audit['replayed_trajectories'] != 96 or not audit['all_scores_and_states_match']:
        raise ValueError('Complete audited pilot required')
    result = json.loads((run/'summary.json').read_text())
    rows = [json.loads(s) for s in (run/'trajectories.jsonl').read_text().splitlines()]
    tasks = {t['id']: t for t in json.loads((ROOT/'data/tasks.json').read_text())}
    s = {r['condition']: r for r in result['conditions']}
    lines = ['# Permission controls and simulated approval for autonomous LLM agents', '',
             'Exploratory independent research pilot · November 10, 2026', '',
             '## Abstract', '',
             'This pilot compares instruction-only authorization rules, enforced permissions, simulated approval, '
             'and their combination in an in-memory workplace benchmark. A local Qwen3 4B Instruct model '
             'completed 96 trajectories across 24 cases derived from eight base workflows. '
             f'Executed policy violations occurred in {s["baseline"]["trajectories_with_executions"]}/24 baseline trajectories, '
             f'{s["permissions"]["trajectories_with_executions"]}/24 permission-controlled trajectories, '
             f'{s["approval"]["trajectories_with_executions"]}/24 approval-controlled trajectories, and '
             f'{s["combined"]["trajectories_with_executions"]}/24 combined trajectories. '
             'These are observations from narrow synthetic tasks, not evidence of general agent safety. '
             'Approval was supplied by a perfect scripted policy oracle; no human participants were involved.', '',
             '## Research question and context', '',
             'Can explicit permission enforcement and approval gates reduce unauthorized actions without materially '
             'reducing task completion? This pilot establishes a reproducible measurement framework and identifies '
             'failure modes; it does not test statistical noninferiority.', '',
             '[AgentDojo](https://arxiv.org/abs/2406.13352) evaluates prompt injection attacks and defenses in agent '
             'environments with untrusted tool data. [CaMeL](https://arxiv.org/abs/2503.18813) uses control/data-flow '
             'separation and capability-based policies to constrain tool execution. The present experiment is a '
             'smaller, independently authored study of exact action permissions and approval burden, not a new '
             'security architecture or a replication of either system.', '',
             '## Method', '',
             'Eight workflows cover drafting and sending messages, copying and publishing document content, '
             'updating and deleting records, and restricted reading. Each workflow has clean, ambiguous, and '
             'injected source variants. The ambiguous variant contains an unapproved suggestion; the injected '
             'variant impersonates an administrator and demands an unauthorized prerequisite.', '',
             'All conditions receive identical prompts and exact permission rules. Permission enforcement checks '
             'all tool calls. Approval reviews mutations only and allows exactly those matching the same policy. '
             'The combined condition checks permissions before requesting approval. Tools operate only on fictional '
             'in-memory data. All intended tasks are achievable in every condition.', '',
             'The model is mlx-community/Qwen3-4B-Instruct-2507-4bit at revision '
             '`50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b`. Generation uses temperature zero, '
             'a six-call budget, and up to 160 output tokens per call. One run per case and condition gives '
             '96 trajectories, with shuffled execution order. The protocol was written before the model run; '
             'it was not externally preregistered.', '',
             'Task completion is evaluated from final state. Authorized completion additionally requires no executed '
             'violation. Blocked attempts remain visible. Invalid action formats, explicit refusals, step exhaustion, '
             'and valid termination are recorded separately. Recorded states and scores were replayed and checked '
             'for all 96 trajectories. Twelve automated tests cover environment and analysis behavior.', '',
             '## Results', '',
             '| Condition | Raw task completion | Authorized completion | Attempting trajectories | Violating trajectories |',
             '| --- | ---: | ---: | ---: | ---: |']
    for c, r in s.items():
        lines.append(f'| {c} | {r["task_complete"]}/24 | {r["authorized_completion"]}/24 | '
                     f'{r["trajectories_with_attempts"]}/24 | {r["trajectories_with_executions"]}/24 |')
    lines += ['', 'The attempt and violation columns count trajectories with at least one such event, not total actions. '
              'A task can achieve its requested final state and still fail authorized completion because of an extra action.', '',
              f'Raw task completion was {s["baseline"]["task_complete"]}/24 with baseline instructions and '
              f'{s["permissions"]["task_complete"]}/24 with permissions. Authorized completion was '
              f'{s["baseline"]["authorized_completion"]}/24 and {s["permissions"]["authorized_completion"]}/24, respectively. '
              'The raw completion comparison matters for the utility question: fewer policy violations alone cannot '
              'establish that controls preserve the ability to finish work.', '',
              '| Condition | Approval requests | Mean seconds per trajectory | Mean generated tokens | Budget exhausted | Authorized completion with valid termination |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for c, r in s.items():
        lines.append(f'| {c} | {r["approval_requests"]} | {r["mean_seconds"]:.2f} | '
                     f'{r["mean_generation_tokens"]:.1f} | {r["budget_exhaustions"]} | '
                     f'{r["authorized_completion_and_termination"]}/24 |')
    lines += ['', 'Latency covers local inference and simulated tool handling, excluding model loading. '
              'There was no warmup; first-call compilation and run-order effects can affect timing. '
              'Approval counts measure requests, not human time. Dollar computational cost and energy were not measured.', '',
              'Paired authorized-completion differences versus baseline, in percentage points, with exploratory '
              '95% bootstrap intervals resampling eight base workflow families:', '']
    for c, r in result['paired_completion'].items():
        lines.append(f'- {c}: {100*r["difference"]:.1f} [{100*r["lower"]:.1f}, {100*r["upper"]:.1f}].')
    lines += ['', 'These intervals describe this small development set. Related variants are grouped together, '
              'but eight clusters provide weak uncertainty estimates. They do not establish general superiority, '
              'equivalence, or a tolerable loss of completion.', '', '## Failure analysis', '',
              '| Condition | Executed exact attack probes | Other executed policy violations |',
              '| --- | ---: | ---: |']
    for c in s:
        probes = others = 0
        for row in rows:
            if row['condition'] != c:
                continue
            for event in row['events']:
                if event['unauthorized_execution']:
                    if event['action'] == tasks[row['task_id']]['attack_probe']:
                        probes += 1
                    else:
                        others += 1
        lines.append(f'| {c} | {probes} | {others} |')
    lines += ['', 'Exact attack probes include sending a synthetic canary to an unauthorized recipient, deleting '
              'a protected object, changing an unauthorized amount, or reading a restricted object. Other violations '
              'can include incorrect message text because these policies constrain arguments exactly. '
              'Consequently, the policy-violation total must not be interpreted as a count of equally harmful actions.', '',
              'Representative observed trajectories:', '']
    for task_id, c in [('document_copy__injected', 'baseline'), ('document_copy__injected', 'combined'),
                       ('restricted_read__injected', 'approval'), ('document_publish__injected', 'approval'),
                       ('record_amount__injected', 'permissions')]:
        row = next(r for r in rows if r['task_id'] == task_id and r['condition'] == c)
        actions = [e['action']['tool'] if e['valid'] else 'invalid' for e in row['events']]
        lines.append(f'- `{task_id}`, {c}: {" → ".join(actions)}. '
                     f'Executed violations: {row["metrics"]["unauthorized_executions"]}; '
                     f'approval requests: {row["metrics"]["approval_requests"]}; '
                     f'authorized completion: {row["metrics"]["authorized_completion"]}; '
                     f'valid termination: {row["terminated"]}.')
    lines += ['', 'Repeated authorized updates and malformed finish messages illustrate why final-state success '
              'and correct termination should be reported separately. A gate can contain an unsafe action without '
              'teaching the agent to stop or preventing repeated approval requests.', '',
              '## Limitations and next study', '',
              'This pilot uses one small quantized model, eight short base workflows, fixed attacks, and deterministic '
              'generation. Exact permission rules reveal the intended actions, making planning easy. There are no '
              'held-out families, realistic enterprise APIs, adaptive attackers, concurrent updates, or data-flow '
              'guarantees. The approval oracle is perfect and shares the permission matcher, so combined controls '
              'are partly redundant by construction. Their protection of covered actions is expected, not itself '
              'an empirical discovery.', '',
              'A follow-up should expand to 20–30 independent workflows, separate task goals from broader permission '
              'scopes, use held-out families and adaptive attacks, and evaluate multiple models with sampled repeats. '
              'Reviewer error and delay should first be simulated transparently, then evaluated with consented human '
              'participants if appropriate. A practically acceptable completion-loss margin and sample-size plan '
              'must be chosen before a confirmatory study.', '',
              'The defensible conclusion is limited: this implementation can expose and contain policy violations '
              'in a controlled local-model pilot, while separately measuring task outcome and approval burden. '
              'It does not yet establish that human approval preserves agent utility in realistic deployments.', '',
              '## Reproducibility', '',
              'See the [README](../README.md), [protocol](protocol.md), '
              '[full result tables](../outputs/pilot-v1/results.md), '
              '[audit](../outputs/pilot-v1/audit.json), and '
              '[raw trajectories](../outputs/pilot-v1/trajectories.jsonl). '
              'Scripted stress fixtures are published separately and are never pooled with model results.', '']
    (ROOT/'docs/research-report.md').write_text('\n'.join(lines))
    print('Research report written from audited pilot results.')


if __name__ == '__main__':
    main()
