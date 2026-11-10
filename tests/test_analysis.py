import unittest
from agentbench.analyze import bootstrap_difference


class AnalysisTests(unittest.TestCase):
    def test_paired_clusters_preserve_constant_difference(self):
        rows = [{'family': family, 'condition': c,
                 'metrics': {'authorized_completion': c == 'permissions'}}
                for family in ('a', 'b', 'c') for c in ('baseline', 'permissions')
                for _ in range(3)]
        result = bootstrap_difference(rows, 'permissions', 'authorized_completion', draws=100)
        self.assertEqual(result['difference'], 1)
        self.assertEqual(result['lower'], 1)
        self.assertEqual(result['upper'], 1)
        self.assertEqual(result['clusters'], 3)

    def test_paired_clusters_detect_no_difference(self):
        rows = [{'family': family, 'condition': c,
                 'metrics': {'authorized_completion': family == 'a'}}
                for family in ('a', 'b') for c in ('baseline', 'combined')]
        result = bootstrap_difference(rows, 'combined', 'authorized_completion', draws=100)
        self.assertEqual(result['difference'], 0)
        self.assertEqual(result['lower'], 0)
        self.assertEqual(result['upper'], 0)


if __name__ == '__main__':
    unittest.main()
