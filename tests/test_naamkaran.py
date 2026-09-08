import unittest
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

class TestNaamkaranCore(unittest.TestCase):
    def test_tools_directory(self):
        tools = os.path.join(ROOT, 'tools')
        self.assertTrue(os.path.isdir(tools), "tools directory must exist")

    def test_padho_file(self):
        padho = os.path.join(ROOT, 'PADHO.txt')
        self.assertTrue(os.path.isfile(padho), "PADHO.txt must exist")

if __name__ == '__main__':
    unittest.main()
