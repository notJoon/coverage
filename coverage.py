"""
Simple code coverage instrumentation POC for Python
Refactored for extensibility and branch coverage support
"""
import ast
import os
import sys
import json
import atexit
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Set, Tuple, Any, List, Optional


class CoverageData:
    """Class to store and manage coverage data"""
    
    def __init__(self):
        self.data = {}
        
    def mark_line(self, filename: str, line_number: int) -> None:
        """Mark a line as executed"""
        if filename not in self.data:
            self.data[filename] = {}
        
        if 'lines' not in self.data[filename]:
            self.data[filename]['lines'] = {}
            
        line_data = self.data[filename]['lines']
        line_data[line_number] = line_data.get(line_number, 0) + 1
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        """Mark a branch as taken or not taken (placeholder for future implementation)"""
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
    
    def get_data(self) -> Dict:
        """Get the current coverage data"""
        return self.data
    
    def save(self, output_file: str = ".coverage_data.json") -> None:
        """Save coverage data to a file"""
        with open(output_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Coverage data saved to {output_file}")


class CoverageTracker:
    """Singleton class to track coverage during program execution"""
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
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        """Mark a branch as taken or not taken (for future branch coverage)"""
        self.coverage_data.mark_branch(filename, line_number, branch_id, taken)
    
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


class LineInstrumentationStrategy(InstrumentationStrategy):
    """Strategy for line coverage instrumentation"""
    
    def __init__(self, filename: str):
        super().__init__(filename)
        self.instrumented_lines = set()
        
    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        """Add instrumentation to mark a line as executed"""
        line_num = getattr(node, 'lineno', None)
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
        """Get the set of line numbers that were instrumented"""
        return self.instrumented_lines


class BranchInstrumentationStrategy(InstrumentationStrategy):
    """Strategy for branch coverage instrumentation (placeholder for future implementation)"""
    
    def __init__(self, filename: str):
        super().__init__(filename)
        self.instrumented_branches = set()
        self.branch_counter = 0
        
    def instrument_node(self, node: ast.AST) -> List[ast.AST]:
        """Add instrumentation to mark branches (placeholder)"""
        # This is a placeholder for future branch coverage implementation
        # Will be expanded when branch coverage is added
        return [node]
    
    def get_instrumented_elements(self) -> Set[str]:
        """Get the set of branch ids that were instrumented"""
        return self.instrumented_branches


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
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, 
                              ast.Import, ast.ImportFrom)):
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
                if hasattr(item, 'lineno'):
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
        
        instrumentation_nodes = []
        for strategy in self.strategies:
            if hasattr(node, 'lineno'):
                new_nodes = strategy.instrument_node(node)
                # Add all but the last item (which is the original node)
                instrumentation_nodes.extend(new_nodes[:-1])
        
        # Make sure the body and orelse parts are properly instrumented
        return ast.If(
            test=node.test,
            body=instrumentation_nodes + node.body,
            orelse=node.orelse
        )
    
    def get_instrumented_elements(self) -> Dict:
        """Get information about instrumented elements from all strategies"""
        result = {}
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__.replace('InstrumentationStrategy', '').lower()
            result[strategy_name] = strategy.get_instrumented_elements()
        return result


class CoverageReporter:
    """Class for generating coverage reports"""
    
    @staticmethod
    def generate_line_report(source_file: str, coverage_data: Dict, instrumented_lines: Set[int]) -> str:
        """Generate a simple line coverage report"""
        # Read the source file
        with open(source_file, 'r') as f:
            source_lines = f.readlines()
        
        # Get the coverage information
        file_coverage = {}
        if str(source_file) in coverage_data:
            file_coverage = coverage_data.get(str(source_file), {}).get('lines', {})
        
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
            "=" * 60
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
    def generate_branch_report(source_file: str, coverage_data: Dict, instrumented_branches: Set[str]) -> str:
        """Generate a branch coverage report (placeholder for future implementation)"""
        # This is a placeholder for future branch coverage reporting
        return "Branch coverage reporting will be implemented in a future version."


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
        with open(f"{self.output_dir}/__init__.py", 'w') as f:
            f.write("# Package initialization file")
    
    def _create_coverage_tracker_module(self) -> None:
        """Create the coverage tracker module in the output directory"""
        with open(f"{self.output_dir}/coverage_tracker.py", 'w') as f:
            f.write("""
import json
import atexit
from typing import Dict, Optional

class CoverageData:
    \"\"\"Class to store and manage coverage data\"\"\"
    
    def __init__(self):
        self.data = {}
        
    def mark_line(self, filename: str, line_number: int) -> None:
        \"\"\"Mark a line as executed\"\"\"
        if filename not in self.data:
            self.data[filename] = {}
        
        if 'lines' not in self.data[filename]:
            self.data[filename]['lines'] = {}
            
        line_data = self.data[filename]['lines']
        line_data[line_number] = line_data.get(line_number, 0) + 1
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        \"\"\"Mark a branch as taken or not taken\"\"\"
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
    
    def get_data(self) -> Dict:
        \"\"\"Get the current coverage data\"\"\"
        return self.data
    
    def save(self, output_file: str = ".coverage_data.json") -> None:
        \"\"\"Save coverage data to a file\"\"\"
        with open(output_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Coverage data saved to {output_file}")


class CoverageTracker:
    \"\"\"Singleton class to track coverage during program execution\"\"\"
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoverageTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        \"\"\"Initialize the coverage tracker\"\"\"
        self.coverage_data = CoverageData()
        # Register the save method to run when Python exits
        atexit.register(self.save_coverage_data)
    
    def mark_line(self, filename: str, line_number: int) -> None:
        \"\"\"Mark a line as executed\"\"\"
        self.coverage_data.mark_line(filename, line_number)
    
    def mark_branch(self, filename: str, line_number: int, branch_id: str, taken: bool) -> None:
        \"\"\"Mark a branch as taken or not taken\"\"\"
        self.coverage_data.mark_branch(filename, line_number, branch_id, taken)
    
    def save_coverage_data(self, output_file: str = ".coverage_data.json") -> None:
        \"\"\"Save coverage data to a file\"\"\"
        self.coverage_data.save(output_file)
    
    def get_coverage_data(self) -> Dict:
        \"\"\"Get the current coverage data\"\"\"
        return self.coverage_data.get_data()


# Create a global instance that will be imported
_coverage_tracker = CoverageTracker()
""")
    
    def instrument_file(self, file_path: str, strategies: List[str] = None) -> Tuple[str, Dict]:
        """Instrument a single Python file"""
        file_path = Path(file_path)
        self.setup_environment()
        
        # Read the source file
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Parse the source into an AST
        tree = ast.parse(source, filename=str(file_path))
        
        # Create instrumentation strategies
        available_strategies = {
            'line': LineInstrumentationStrategy(str(file_path)),
            # 'branch': BranchInstrumentationStrategy(str(file_path)) # Commented out until implemented
        }
        
        selected_strategies = []
        if strategies:
            for strategy_name in strategies:
                if strategy_name in available_strategies:
                    selected_strategies.append(available_strategies[strategy_name])
        else:
            # Default to line coverage only
            selected_strategies.append(available_strategies['line'])
        
        # Apply our instrumentation
        instrumenter = CoverageInstrumenter(filename=str(file_path), strategies=selected_strategies)
        instrumented_tree = instrumenter.visit(tree)
        
        # Fix line numbers and other AST properties
        ast.fix_missing_locations(instrumented_tree)
        
        # Generate the instrumented code
        instrumented_code = compile(instrumented_tree, filename=str(file_path), mode='exec')
        
        # Create a new file with the instrumented code
        output_file = Path(self.output_dir) / file_path.name
        with open(output_file, 'w') as f:
            f.write(ast.unparse(instrumented_tree))
        
        return str(output_file), instrumenter.get_instrumented_elements()
    
    def run_instrumented_file(self, instrumented_file: str) -> Dict:
        """Run an instrumented file"""
        # PYTHONPATH에 .coverage_instrumented 디렉토리 추가
        sys.path.insert(0, self.output_dir)
        
        # Execute the instrumented file
        current_dir = os.getcwd()
        try:
            os.chdir(self.output_dir)
            
            # Create a small wrapper script that ensures coverage_tracker is imported properly
            with open(f"{self.output_dir}/run_test.py", 'w') as f:
                f.write(f"""
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
""")
            
            # Execute our wrapper
            exec(open("run_test.py").read())
        finally:
            os.chdir(current_dir)
        
        # Load the coverage data
        coverage_file = f"{self.output_dir}/.coverage_data.json"
        if os.path.exists(coverage_file):
            with open(coverage_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    def generate_report(self, source_file: str, coverage_data: Dict, instrumentation_info: Dict) -> str:
        """Generate a coverage report"""
        reports = []
        
        # Generate line coverage report if available
        if 'line' in instrumentation_info:
            line_report = CoverageReporter.generate_line_report(
                source_file, coverage_data, instrumentation_info['line']
            )
            reports.append(line_report)
        
        # Generate branch coverage report if available (placeholder)
        if 'branch' in instrumentation_info:
            branch_report = CoverageReporter.generate_branch_report(
                source_file, coverage_data, instrumentation_info['branch']
            )
            reports.append(branch_report)
        
        return "\n\n".join(reports)


def main():
    """Main function to demonstrate the POC"""
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
        instrumented_file, instrumentation_info = coverage_engine.instrument_file(source_file)
        print(f"File instrumented: {instrumented_file}")
        
        # Run the instrumented file
        print("Running instrumented file...")
        coverage_data = coverage_engine.run_instrumented_file(instrumented_file)
        
        # Generate and print the report
        report = coverage_engine.generate_report(source_file, coverage_data, instrumentation_info)
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