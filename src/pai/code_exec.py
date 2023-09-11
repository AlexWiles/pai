import ast
import code
import io
import sys


class CodeExec(code.InteractiveConsole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_exception = None

    def showtraceback(self, *args, **kwargs):
        """Override the default traceback behavior to store the last exception."""
        self.last_exception = sys.exc_info()[1]
        super().showtraceback(*args, **kwargs)

    def _is_expression(self, code: str) -> bool:
        """Check if the given code is an expression."""
        try:
            ast.parse(code, mode="eval")
            return True
        except:
            return False

    def custom_run_source(self, source: str) -> str:
        """
        Push a block of code and get the string output.

        This behaves like a REPL. If the last line of the code
        is an expression, it is evaluated and the result is added to the output.

        For example:
        source:
            1+1
        returns:
            "2"

        If a block of code is given, the output is printed and the last expression
        is returned.

        source:
            def add(a, b):
                print("Adding a and b")
                return a + b
            add(1, 2)
        returns:
            "Adding a and b\n3"
        """
        collector = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        all_lines = source.strip().split("\n")
        last_line = all_lines[-1]

        # If the last line of the full_code is an expression, evaluate it after executing the rest
        if self._is_expression(last_line):
            # Execute all lines except the last one
            exec_code = "\n".join(all_lines[:-1])
            try:
                compiled_code = compile(exec_code, "<string>", "exec")
                self.runcode(compiled_code)

                # if there was not exception, then we can evaluate the last line
                if not self.last_exception:
                    self.push(last_line)
            except Exception as e:
                # handle an error compiling the exec_code
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}"
        else:
            # If the last line is not an expression, try to compile and execute the full_code
            try:
                compiled_code = compile(source, "<string>", "exec")
                self.runcode(compiled_code)
            except SyntaxError as e:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}\n"

        # clear the last exception
        self.last_exception = None

        # restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # get the output from the collector
        output = collector.getvalue()
        return output
