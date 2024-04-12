import ast
import signal
import astunparse


from typing import List
from .executor_types import ExecuteResult, Executor
from .runtime import GenericRuntime, timeout_limit
import traceback


class PyExecutor(Executor):

    def __init__(self):
        self.runtime = GenericRuntime()

    def execute(self, func: str, tests: List[str], timeout: int = 5) -> ExecuteResult:
        # Combine function code and assert statement
        imports = 'from typing import *'
        func_test_list = [f'{imports}\n{func}\n{test}' for test in tests]

        # Run the tests and collect the results
        success_tests = []
        failed_tests = []
        is_passing = True
        num_tests = len(func_test_list)
        for i in range(num_tests):
            # print(f"Current function @ {i}")
            # print(func_test_list[i])
            with timeout_limit(timeout):
                try:
                    self.runtime.exec_code(func_test_list[i])
                    success_tests += [tests[i]]
                except:
                    output = get_output(self.runtime, f'{imports}\n{func}', tests[i], timeout=timeout)
                    print(f"{tests[i]} # output: {output}")
                    failed_tests += [f"{tests[i]} # output: {output}"]
                    is_passing = False
            ## just to clear history
            self.runtime.clear()
        state = []
        for test in tests:
            if test in success_tests:
                state += [True]
            else:
                state += [False]

        state = tuple(state)

        feedback = "Tested passed:"
        for test in success_tests:
            feedback += f"\n{test}"
        feedback += "\n\nTests failed:"
        for test in failed_tests:
            feedback += f"\n{test}"
            
        return ExecuteResult(is_passing, feedback, state)

    def evaluate(self, name: str, func: str, test: str, timeout: int = 5) -> bool:
        """
        Evaluates the implementation on Human-Eval Python.

        probably should be written in a dataset-agnostic way but not now
        """
        code = f"""{func}

{test}

check({name})
    """
        with timeout_limit(timeout):
            try:
                self.runtime.exec_code(code)
                return True
            except Exception as e:
                return False


def get_call_str(assert_statement: str) -> str:
    ast_parsed = ast.parse(assert_statement)
    try:
        call_str = ast_parsed.body[0].test.left # type: ignore
    except:
        call_str = ast_parsed.body[0].test # type: ignore

    return astunparse.unparse(call_str).strip()


def get_output(runtime: GenericRuntime, func: str, assert_statement: str, timeout: int = 5) -> str:
    with timeout_limit(timeout):
        try:
            func_call = get_call_str(assert_statement)
            runtime.exec_code(func)
            output = runtime.eval_code(func_call)
            return output
        except TimeoutError:
            return "TIMEOUT"
        except (Exception, KeyboardInterrupt, SystemExit) as e:
            if isinstance(e, SystemExit):
                error_message = "System exit requested."
            elif isinstance(e, KeyboardInterrupt):
                error_message = "Execution interrupted by user."
            else:
                error_message = str(e)
            # error_message = traceback.format_exc()  # much more detailed message.
            return str(error_message)


if __name__ == "__main__":
    pass
    # Test the function
    func = "def add(a, b):\n    while True:\n        x = 1\n    return a + b"
    tests = ["assert add(1, 2) == 3", "assert add(1, 2) == 4"]
    print(PyExecutor().execute(func, tests, timeout=1))
