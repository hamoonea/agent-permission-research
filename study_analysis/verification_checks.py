"""Run the private development-only verification suite without generating reserved tasks."""
import argparse
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from followup.evidence import digest, inputs, load_tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Check record already exists; preserve it and use a new output')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root/'tests'))
    from test_followup import FollowupTests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    modules = ['test_core', 'test_analysis', 'test_followup_amendments',
               'test_followup_verification', 'study_analysis.test_development_audit',
               'study_analysis.test_repeated_development_review']
    for module in modules:
        suite.addTests(loader.loadTestsFromName(module))
    for name in loader.getTestCaseNames(FollowupTests):
        if name != 'test_family_split_and_variants':
            suite.addTest(FollowupTests(name))
    before = inputs()
    with patch.object(FollowupTests, 'setUp', lambda self: setattr(self, 'tasks', load_tasks('dev'))):
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    if inputs() != before:
        raise ValueError('Study inputs changed during checks')
    files = [*sorted((root/'tests').glob('test*.py')),
             *sorted((root/'study_analysis').glob('*.py'))]
    record = {
        'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'all_passed': result.wasSuccessful(), 'study_inputs': before,
        'test_and_analysis_sources': {str(p.relative_to(root)): digest(p) for p in files},
        'original_followup_module_scope': 'All tests except full-split generation; setup loads development JSON only.',
        'heldout_inference_performed': False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
