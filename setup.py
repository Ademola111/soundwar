"""to start an app"""
import sys
from soundwarapp import create_app
import unittest

app = create_app("production")

def run_tests():
    tests = unittest.TestLoader().discover('test_userroutes')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    if 'test' in sys.argv:
        run_tests()
    else:
        app.run(debug=True, port=5000)