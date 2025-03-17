import ast
import os
import sys
import json
import atexit
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Set, Tuple, List


class CoverageData:
    """Class to store and manage coverage data"""

    def __init__(self):
        self.data = {}

    def mark_line(self, filename: str, line_number: int) -> None:
        """Mark a line as executed"""
        if filename not in self.data:
            self.data[filename] = {}

        if "lines" not in self.data[filename]:
            self.data[filename]["lines"] = {}

        line_data = self.data[filename]["lines"]
        line_data[line_number] = line_data.get(line_number, 0) + 1

    def mark_branch(
        self, filename: str, line_number: int, branch_id: str, taken: bool
    ) -> None:
        """Mark a branch as taken or not taken (placeholder for future implementation)"""
        if filename not in self.data:
            self.data[filename] = {}

        if "branches" not in self.data[filename]:
            self.data[filename]["branches"] = {}

        branch_data = self.data[filename]["branches"]
        branch_key = f"{line_number}_{branch_id}"

        if branch_key not in branch_data:
            branch_data[branch_key] = {"taken": 0, "not_taken": 0}

        if taken:
            branch_data[branch_key]["taken"] += 1
        else:
            branch_data[branch_key]["not_taken"] += 1

    def mark_condition(
        self, filename: str, line_number: int, cond_id: str, value: bool
    ) -> None:
        """Mark a condition as true or false"""
        if filename not in self.data:
            self.data[filename] = {}

        if "conditions" not in self.data[filename]:
            self.data[filename]["conditions"] = {}

        # condition key => "12_condA" form
        cond_key = f"{line_number}_{cond_id}"
        if cond_key not in self.data[filename]["conditions"]:
            self.data[filename]["conditions"][cond_key] = {"true": 0, "false": 0}

        if value:
            self.data[filename]["conditions"][cond_key]["true"] += 1
        else:
            self.data[filename]["conditions"][cond_key]["false"] += 1

    def get_data(self) -> Dict:
        """Get the current coverage data"""
        return self.data

    def save(self, output_file: str = ".coverage_data.json") -> None:
        """Save coverage data to a file"""
        with open(output_file, "w") as f:
            json.dump(self.data, f, indent=2)
        print(f"Coverage data saved to {output_file}")


class CoverageTracker:
    """Track coverage during program execution"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoverageTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the coverage tracker"""
        self.coverage_data = CoverageData()
        # Register the save method to run when Python exits
        atexit.register(self.save_coverage_data)

    def mark_line(self, filename: str, line_number: int) -> None:
        """Mark a line as executed"""
        self.coverage_data.mark_line(filename, line_number)

    def mark_branch(
        self, filename: str, line_number: int, branch_id: str, taken: bool
    ) -> None:
        """Mark a branch as taken or not taken (for future branch coverage)"""
        self.coverage_data.mark_branch(filename, line_number, branch_id, taken)

    def mark_condition(
        self, filename: str, line_number: int, cond_id: str, value: bool
    ) -> None:
        """Mark a condition as true or false"""
        self.coverage_data.mark_condition(filename, line_number, cond_id, value)

    def save_coverage_data(self, output_file: str = ".coverage_data.json") -> None:
        """Save coverage data to a file"""
        self.coverage_data.save(output_file)

    def get_coverage_data(self) -> Dict:
        """Get the current coverage data"""
        return self.coverage_data.get_data()


# Create a global instance that will be imported
_coverage_tracker = CoverageTracker()


class InstrumentationStrategy(ABC):
    """Abstract base class for instrumentation strategies"""

    def __init__(self, filename: str):
        self.filename = filename

    @abstractmethod
    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        """Instrument a node for coverage tracking"""
        pass

    @abstractmethod
    def get_instrumented_elements(self) -> Set[int]:
        """Get the set of line numbers that were instrumented"""
        pass


class LineInstrumentationStrategy(InstrumentationStrategy):
    """Strategy for line coverage instrumentation"""

    def __init__(self, filename: str):
        super().__init__(filename)
        self.instrumented_lines = set()

    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        """Add instrumentation to mark a line as executed"""
        line_num = getattr(node, "lineno", None)
        if line_num is not None:
            self.instrumented_lines.add(line_num)

            # Create a call to mark this line as executed
            tracker_call = ast.parse(
                f"_coverage_tracker.mark_line('{self.filename}', {line_num})"
            ).body[0]

            # If the node is an expression, we need to keep its value
            if isinstance(node, ast.Expr):
                return [tracker_call, node]
            return [tracker_call, node]
        return [node]

    def get_instrumented_elements(self) -> Set[int]:
        return self.instrumented_lines


class BranchInstrumentationStrategy(InstrumentationStrategy):
    """Strategy for branch coverage instrumentation (placeholder for future implementation)"""

    def __init__(self, filename: str):
        super().__init__(filename)
        self.instrumented_branches = set()
        self.branch_counter = 0

    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        """Add instrumentation to mark branches"""
        if isinstance(node, ast.If):
            branch_id = f"branch_{self.branch_counter}"
            self.branch_counter += 1
            self.instrumented_branches.add(branch_id)

            line_num = getattr(node, "lineno", None)

            # call mark_branch when going to the `True` branch
            mark_true = ast.parse(
                f"_coverage_tracker.mark_branch('{self.filename}', {line_num}, '{branch_id}', True)"
            ).body[0]

            # call mark_branch when going to the `False` branch
            mark_false = ast.parse(
                f"_coverage_tracker.mark_branch('{self.filename}', {line_num}, '{branch_id}', False)"
            ).body[0]

            # replace the original if statement:
            #
            # if node.test:
            #     mark_branch( ... True )
            #     (previous body)
            # else:
            #     mark_branch( ... False )
            #     (previous orelse)
            new_if = ast.If(
                test=node.test,
                body=[mark_true] + node.body,
                orelse=[mark_false] + node.orelse,
            )
            return [new_if]

        # returning without modifications for other node types
        return [node]

    def get_instrumented_elements(self) -> Set[str]:
        return self.instrumented_branches

class ConditionInstrumentationStrategy(InstrumentationStrategy):
    """
    Strategy for condition coverage instrumentation.
    It replaces 'and/or' bool ops with calls to _cov_and/_cov_or,
    so that each operand is marked separately for True/False.
    """

    def __init__(self, filename: str):
        super().__init__(filename)
        self.instrument_conditions = set()
        self.condition_counter = 0

    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        if isinstance(node, ast.BoolOp):
            return [self._transform_boolop(node)]
        return [node]

    def _transform_boolop(self, node: ast.BoolOp) -> ast.AST:
        """
        Replace 'and/or' bool ops with calls to _cov_and/_cov_or,
        so that each operand is marked separately for True/False.
        """
        line_num = getattr(node, "lineno", None)
        if line_num is None:
            return node # impossible to instrument

        is_and = isinstance(node.op, ast.And)

        # node.values = [expr1, expr2, expr3] like this, multiple expressions can be included
        # In cases where "and", "or" are consecutively attached: (expr1 and expr2 and expr3)
        # Convert by grouping them from left to right with *cov*and(...) 
        # Finally, create a single expression (node).
        return self._transform_boolop_values(node.values, line_num, is_and)

    def _transform_boolop_values(self, values: List[ast.AST], line_num: int, is_and: bool) -> ast.AST:
        """
        Combine the values list from left to right
        while replacing with *cov*and(...) or *cov*or(...)
        Example) a and b and c => *cov*and(a, *cov*and(b, c))
        """
        if len(values) == 1:
            return values[0] # no need to wrap
        
        left = values[0]
        right = self._transform_boolop_values(values[1:], line_num, is_and)

        # create new condition ID
        cond_left_id = f"cond_{self.condition_counter}"
        self.condition_counter += 1
        cond_right_id = f"cond_{self.condition_counter}"
        self.condition_counter += 1

        self.instrumented_conditions.add(cond_left_id)
        self.instrumented_conditions.add(cond_right_id)

        func_name = "_cov_and" if is_and else "_cov_or"
        # _cov_and(left, right, filename, line_num, cond_left_id, cond_right_id, _coverage_tracker)
        call_node = ast.Call(
            func=ast.Name(id=func_name, ctx=ast.Load()),
            args=[
                left,
                right,
                ast.Constant(value=self.filename),
                ast.Constant(value=line_num),
                ast.Constant(value=cond_left_id),
                ast.Constant(value=cond_right_id),
                ast.Name(id="_coverage_tracker", ctx=ast.Load()),
            ],
            keywords=[],
        )
        return call_node

    def get_instrumented_elements(self) -> Set[str]:
        return self.instrumented_conditions

class CoverageInstrumenter(ast.NodeTransformer):
    """AST transformer to add coverage instrumentation"""

    def __init__(self, filename: str, strategies: List[InstrumentationStrategy] = None):
        self.filename = filename
        self.strategies = strategies or [LineInstrumentationStrategy(filename)]

    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Visit a module node and add coverage import at the top"""
        # Add import for our coverage tracker at the top of the file
        import_tracker = ast.parse(
            "import sys; "
            "sys.path.insert(0, '.'); "
            "from coverage_tracker import _coverage_tracker"
        ).body

        # Transform all the statements in the module
        new_body = import_tracker + [self.visit(n) for n in node.body]
        return ast.Module(body=new_body, type_ignores=[])

    def generic_visit(self, node: ast.AST) -> ast.AST:
        """Override generic_visit to instrument non-container nodes"""
        ast.NodeTransformer.generic_visit(self, node)

        # Skip nodes that are typically containers or don't represent executable lines
        if isinstance(
            node,
            (
                ast.Module,
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            return node

        # Apply all instrumentation strategies
        instrumented_nodes = [node]
        for strategy in self.strategies:
            new_nodes = []
            for n in instrumented_nodes:
                new_nodes.extend(strategy.instrument_node(n))
            instrumented_nodes = new_nodes

        # Return the last node which should be the original node
        return instrumented_nodes[-1] if instrumented_nodes else node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit a function definition"""
        # First, apply normal visit to decorators and other parts
        self.generic_visit(node)

        # Instrument the function body
        new_body = []
        for item in node.body:
            # Apply all instrumentation strategies
            for strategy in self.strategies:
                if hasattr(item, "lineno"):
                    new_items = strategy.instrument_node(item)
                    # Add all but the last item (which is the original node)
                    new_body.extend(new_items[:-1])

            # Add the original node
            new_body.append(item)

        node.body = new_body
        return node

    # Similarly, handle other container nodes if needed
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node: ast.If) -> ast.If:
        """Visit an if statement"""
        self.generic_visit(node)

        for strategy in self.strategies:
            new_nodes = strategy.instrument_node(node)

            if len(new_nodes) == 1:
                # treat as a final node
                node = new_nodes[0]
            else:
                # if it's like [tracker_call, node] for line instrumentation,
                # the last element is the actual original node, so set that as the final node.
                # Also, handle the rest by attaching them to the front of `node.body`
                instrumentation_nodes = new_nodes[:-1]
                original_node = new_nodes[-1]
                if isinstance(original_node, ast.If):
                    original_node.body = instrumentation_nodes + original_node.body
                    node = original_node
                else:
                    node = original_node
        return node

    def get_instrumented_elements(self) -> Dict:
        """Get information about instrumented elements from all strategies"""
        result = {}
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__.replace(
                "InstrumentationStrategy", ""
            ).lower()
            result[strategy_name] = strategy.get_instrumented_elements()
        return result


class CoverageReporter:
    """Class for generating coverage reports"""

    @staticmethod
    def generate_line_report(
        source_file: str, coverage_data: Dict, instrumented_lines: Set[int]
    ) -> str:
        """Generate a simple line coverage report"""
        # Read the source file
        with open(source_file, "r") as f:
            source_lines = f.readlines()

        # Get the coverage information
        file_coverage = {}
        if str(source_file) in coverage_data:
            file_coverage = coverage_data.get(str(source_file), {}).get("lines", {})

        # Convert line numbers to integers
        file_coverage = {int(k): v for k, v in file_coverage.items()}

        # Calculate coverage percentage
        executed_lines = set(file_coverage.keys())
        if not instrumented_lines:
            coverage_percent = 0
        else:
            coverage_percent = (len(executed_lines) / len(instrumented_lines)) * 100

        # Generate the report
        report = [
            f"Coverage Report for {source_file}",
            f"Total lines: {len(source_lines)}",
            f"Instrumented lines: {len(instrumented_lines)}",
            f"Executed lines: {len(executed_lines)}",
            f"Coverage: {coverage_percent:.2f}%",
            "\nLine by line coverage:",
            "=" * 60,
        ]

        for i, line in enumerate(source_lines, 1):
            if i in instrumented_lines:
                if i in executed_lines:
                    count = file_coverage.get(i, 0)
                    status = f"[COVERED: {count}]"
                else:
                    status = "[NOT COVERED]"
            else:
                status = "[NOT INSTRUMENTED]"

            report.append(f"{i:4d} {status:16s} {line.rstrip()}")

        return "\n".join(report)

    @staticmethod
    def generate_branch_report(
        source_file: str, coverage_data: Dict, instrumented_branches: Set[str]
    ) -> str:
        file_branches = coverage_data.get(source_file, {}).get("branches", {})

        covered = 0
        total = 0

        lines = []
        lines.append(f"Branch Coverage Report for {source_file}")
        lines.append("=" * 60)

        for branch_key, counts in file_branches.items():
            total += 1
            if (counts["taken"] > 0) or (counts["not_taken"] > 0):
                covered += 1
            lines.append(
                f"{branch_key:20s} => taken: {counts['taken']:2d}, not_taken: {counts['not_taken']:2d}"
            )

        coverage_pct = (covered / total * 100) if total > 0 else 0
        lines.append(f"\nTotal branches: {total}, Covered: {covered}")
        lines.append(f"Coverage: {coverage_pct:.2f}%")

        return "\n".join(lines)


class CoverageEngine:
    """Main class for the coverage engine"""

    def __init__(self, output_dir: str = ".coverage_instrumented"):
        self.output_dir = output_dir

    def setup_environment(self) -> None:
        """Set up the environment for coverage tracking"""
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Create the coverage tracker module
        self._create_coverage_tracker_module()

        # Create a __init__.py in the output directory so it's treated as a package
        with open(f"{self.output_dir}/__init__.py", "w") as f:
            f.write("# Package initialization file")

    def _create_coverage_tracker_module(self) -> None:
        with open(f"{self.output_dir}/coverage_tracker.py", "w") as f:
            f.write(
                '''
import json
import atexit
from typing import Dict

class CoverageData:
    """
    Class to store and manage coverage data.
    This includes line, branch, and condition coverage.
    """
    def __init__(self):
        # The structure of self.data is:
        # {
        #   "<filename>": {
        #       "lines": { <line_number>: execution_count, ... },
        #       "branches": {
        #           "<lineNum>_<branchId>": {"taken": int, "not_taken": int},
        #           ...
        #       },
        #       "conditions": {
        #           "<lineNum>_<condId>": {"true": int, "false": int},
        #           ...
        #       }
        #   },
        #   ...
        # }
        self.data = {}
    
    def mark_line(self, filename: str, line_number: int) -> None:
        """Mark a line as executed."""
        if filename not in self.data:
            self.data[filename] = {}
        
        if 'lines' not in self.data[filename]:
            self.data[filename]['lines'] = {}
            
        line_data = self.data[filename]['lines']
        line_data[line_number] = line_data.get(line_number, 0) + 1
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        """
        Mark a branch as taken or not taken.
        e.g. for an 'if' statement, True branch / False branch
        """
        if filename not in self.data:
            self.data[filename] = {}
            
        if 'branches' not in self.data[filename]:
            self.data[filename]['branches'] = {}
            
        branch_data = self.data[filename]['branches']
        branch_key = f"{line_number}_{branch_id}"
        
        if branch_key not in branch_data:
            branch_data[branch_key] = {'taken': 0, 'not_taken': 0}
            
        if taken:
            branch_data[branch_key]['taken'] += 1
        else:
            branch_data[branch_key]['not_taken'] += 1

    def mark_condition(self, filename: str, line_number: int, cond_id: str, value: bool) -> None:
        """
        Mark a sub-condition in a complex boolean expression as True or False.
        This is used for condition coverage.
        """
        if filename not in self.data:
            self.data[filename] = {}

        if 'conditions' not in self.data[filename]:
            self.data[filename]['conditions'] = {}
        
        condition_key = f"{line_number}_{cond_id}"
        if condition_key not in self.data[filename]['conditions']:
            self.data[filename]['conditions'][condition_key] = {'true': 0, 'false': 0}
        
        if value:
            self.data[filename]['conditions'][condition_key]['true'] += 1
        else:
            self.data[filename]['conditions'][condition_key]['false'] += 1
    
    def get_data(self) -> Dict:
        """Get the current coverage data."""
        return self.data
    
    def save(self, output_file: str = ".coverage_data.json") -> None:
        """Save coverage data to a file in JSON format."""
        with open(output_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Coverage data saved to {output_file}")


class CoverageTracker:
    """
    Singleton class to track coverage during program execution.
    Provides mark_line, mark_branch, mark_condition methods.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoverageTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the coverage tracker"""
        self.coverage_data = CoverageData()
        # Register the save method to run when Python exits
        atexit.register(self.save_coverage_data)
    
    def mark_line(self, filename: str, line_number: int) -> None:
        """Mark a line as executed."""
        self.coverage_data.mark_line(filename, line_number)
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        """Mark a branch as taken or not taken."""
        self.coverage_data.mark_branch(filename, line_number, branch_id, taken)
    
    def mark_condition(self, filename: str, line_number: int, cond_id: str, value: bool) -> None:
        """Mark a condition as True or False."""
        self.coverage_data.mark_condition(filename, line_number, cond_id, value)
    
    def save_coverage_data(self, output_file: str = ".coverage_data.json") -> None:
        """Save coverage data to a file (triggered at process exit)."""
        self.coverage_data.save(output_file)
    
    def get_coverage_data(self) -> Dict:
        """Return the aggregated coverage data."""
        return self.coverage_data.get_data()


def _cov_and(left, right, filename, line_number, cond_left_id, cond_right_id, tracker):
    """
    Short-circuit logic for 'and' with condition coverage.
    Mark the left condition first, then only evaluate right if left is True.
    """
    tracker.mark_condition(filename, line_number, cond_left_id, left)
    if not left:
        return False
    tracker.mark_condition(filename, line_number, cond_right_id, right)
    return left and right

def _cov_or(left, right, filename, line_number, cond_left_id, cond_right_id, tracker):
    """
    Short-circuit logic for 'or' with condition coverage.
    Mark the left condition first, then only evaluate right if left is False.
    """
    tracker.mark_condition(filename, line_number, cond_left_id, left)
    if left:
        return True
    tracker.mark_condition(filename, line_number, cond_right_id, right)
    return left or right

# Create a global instance that will be imported by instrumented code
_coverage_tracker = CoverageTracker()
'''
        )


    def instrument_file(
        self, file_path: str, strategies: List[str] = None
    ) -> Tuple[str, Dict]:
        """Instrument a single Python file"""
        file_path = Path(file_path)
        self.setup_environment()

        # Read the source file
        with open(file_path, "r") as f:
            source = f.read()

        # Parse the source into an AST
        tree = ast.parse(source, filename=str(file_path))

        # Create instrumentation strategies
        path_str = str(file_path)
        available_strategies = {
            "line": LineInstrumentationStrategy(path_str),
            "branch": BranchInstrumentationStrategy(path_str),
            "condition": ConditionInstrumentationStrategy(path_str),
        }

        selected_strategies = []
        if strategies:
            for strategy_name in strategies:
                if strategy_name in available_strategies:
                    selected_strategies.append(available_strategies[strategy_name])
        else:
            # Default to line coverage only
            selected_strategies.append(available_strategies["line"])

        # Apply our instrumentation
        instrumenter = CoverageInstrumenter(
            filename=str(file_path), strategies=selected_strategies
        )
        instrumented_tree = instrumenter.visit(tree)

        # Fix line numbers and other AST properties
        ast.fix_missing_locations(instrumented_tree)

        # Generate the instrumented code
        instrumented_code = compile(
            instrumented_tree, filename=str(file_path), mode="exec"
        )

        # Create a new file with the instrumented code
        output_file = Path(self.output_dir) / file_path.name
        with open(output_file, "w") as f:
            f.write(ast.unparse(instrumented_tree))

        return str(output_file), instrumenter.get_instrumented_elements()

    def run_instrumented_file(self, instrumented_file: str) -> Dict:
        """Run an instrumented file"""
        # add .coverage_instrumented directory to PYTHONPATH
        sys.path.insert(0, self.output_dir)

        # Execute the instrumented file
        current_dir = os.getcwd()
        try:
            os.chdir(self.output_dir)

            # Create a small wrapper script that ensures coverage_tracker is imported properly
            with open(f"{self.output_dir}/run_test.py", "w") as f:
                f.write(
                    f"""
import sys
import os
import importlib.util

# Make sure the current directory is in the path
sys.path.insert(0, os.path.abspath('.'))

# Ensure coverage_tracker is imported
from coverage_tracker import _coverage_tracker

# Import the instrumented module
spec = importlib.util.spec_from_file_location("instrumented_module", "{Path(instrumented_file).name}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
"""
                )

            # Execute our wrapper
            exec(open("run_test.py").read())
        finally:
            os.chdir(current_dir)

        # Load the coverage data
        coverage_file = f"{self.output_dir}/.coverage_data.json"
        if os.path.exists(coverage_file):
            with open(coverage_file, "r") as f:
                return json.load(f)

        return {}

    def generate_report(
        self, source_file: str, coverage_data: Dict, instrumentation_info: Dict
    ) -> str:
        """Generate a coverage report"""
        reports = []

        # Generate line coverage report if available
        if "line" in instrumentation_info:
            line_report = CoverageReporter.generate_line_report(
                source_file, coverage_data, instrumentation_info["line"]
            )
            reports.append(line_report)

        # Generate branch coverage report if available (placeholder)
        if "branch" in instrumentation_info:
            branch_report = CoverageReporter.generate_branch_report(
                source_file, coverage_data, instrumentation_info["branch"]
            )
            reports.append(branch_report)

        return "\n\n".join(reports)


def main():
    if len(sys.argv) < 2:
        print("Usage: python coverage_tool.py <python_file_to_instrument>")
        return

    source_file = sys.argv[1]

    # Create our coverage engine
    coverage_engine = CoverageEngine()

    # Clean up previous output directory if it exists
    output_dir = ".coverage_instrumented"
    if os.path.exists(output_dir):
        import shutil

        print(f"Cleaning up previous instrumentation directory: {output_dir}")
        shutil.rmtree(output_dir, ignore_errors=True)

    # Instrument the file
    print(f"Instrumenting {source_file}...")
    try:
        instrumented_file, instrumentation_info = coverage_engine.instrument_file(
            source_file, strategies=["line", "branch"]
        )
        print(f"File instrumented: {instrumented_file}")

        # Run the instrumented file
        print("Running instrumented file...")
        coverage_data = coverage_engine.run_instrumented_file(instrumented_file)

        # Generate and print the report
        report = coverage_engine.generate_report(
            source_file, coverage_data, instrumentation_info
        )
        print("\n" + report)
    except Exception as e:
        print(f"Error during execution: {e}")
        print("\nDebugging information:")
        print(f"- Check if '{output_dir}/coverage_tracker.py' exists")
        print(f"- Verify imports in the instrumented file: {instrumented_file}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
