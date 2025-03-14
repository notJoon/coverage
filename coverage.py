"""
Simple code coverage instrumentation POC for Python
"""
import ast
import os
import sys
import json
from pathlib import Path


class CoverageTracker:
    """Singleton class to track coverage during program execution"""
    _instance = None
    _coverage_data = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoverageTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the coverage tracker"""
        self._coverage_data = {}
        
    def mark_line(self, filename, line_number):
        """Mark a line as executed"""
        if filename not in self._coverage_data:
            self._coverage_data[filename] = {}
        
        self._coverage_data[filename][line_number] = self._coverage_data[filename].get(line_number, 0) + 1
    
    def save_coverage_data(self, output_file=".coverage_data.json"):
        """Save coverage data to a file"""
        with open(output_file, 'w') as f:
            json.dump(self._coverage_data, f, indent=2)
        print(f"Coverage data saved to {output_file}")
    
    def get_coverage_data(self):
        """Get the current coverage data"""
        return self._coverage_data


class CoverageInstrumenter(ast.NodeTransformer):
    """AST transformer to add coverage instrumentation"""
    
    def __init__(self, filename):
        self.filename = filename
        self.line_numbers = set()
        
    def visit_Module(self, node):
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
    
    def instrument_node(self, node):
        """Add instrumentation to mark a line as executed"""
        line_num = getattr(node, 'lineno', None)
        if line_num is not None:
            self.line_numbers.add(line_num)
            
            # Create a call to mark this line as executed
            tracker_call = ast.parse(
                f"_coverage_tracker.mark_line('{self.filename}', {line_num})"
            ).body[0]
            
            # If the node is an expression, we need to keep its value
            if isinstance(node, ast.Expr):
                return [tracker_call, node]
            
            return [tracker_call, node]
        return [node]
    
    def generic_visit(self, node):
        """Override generic_visit to instrument non-container nodes"""
        ast.NodeTransformer.generic_visit(self, node)
        
        # Skip nodes that are typically containers or don't represent executable lines
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, 
                              ast.Import, ast.ImportFrom)):
            return node
        
        # Instrument other nodes that represent executable lines
        if hasattr(node, 'lineno'):
            result = self.instrument_node(node)
            if len(result) > 1:
                return result[1]  # Return the original node after it's instrumented
        
        return node
    
    def visit_FunctionDef(self, node):
        """Visit a function definition"""
        # First, apply normal visit to decorators and other parts
        self.generic_visit(node)
        
        # Instrument the function body
        new_body = []
        for item in node.body:
            # Add tracking call before each statement in the function
            if hasattr(item, 'lineno'):
                tracker_call = ast.parse(
                    f"_coverage_tracker.mark_line('{self.filename}', {item.lineno})"
                ).body[0]
                new_body.append(tracker_call)
            
            new_body.append(item)
        
        node.body = new_body
        return node
    
    # Similarly, handle other container nodes if needed
    visit_AsyncFunctionDef = visit_FunctionDef
    
    def visit_If(self, node):
        """Visit an if statement"""
        self.generic_visit(node)
        
        # Instrument the test condition
        tracker_call = ast.parse(
            f"_coverage_tracker.mark_line('{self.filename}', {node.lineno})"
        ).body[0]
        
        # Make sure the body and orelse parts are properly instrumented
        return ast.If(
            test=node.test,
            body=[tracker_call] + node.body,
            orelse=node.orelse
        )
    
    def get_instrumented_line_numbers(self):
        """Get the set of line numbers that were instrumented"""
        return self.line_numbers


class Coverage:
    """Main class for the coverage POC"""
    
    def __init__(self):
        self.output_dir = ".coverage_instrumented"
        
    def instrument_file(self, file_path):
        """Instrument a single Python file"""
        file_path = Path(file_path)
        
        # Read the source file
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Parse the source into an AST
        tree = ast.parse(source, filename=str(file_path))
        
        # Apply our instrumentation
        instrumenter = CoverageInstrumenter(filename=str(file_path))
        instrumented_tree = instrumenter.visit(tree)
        
        # Fix line numbers and other AST properties
        ast.fix_missing_locations(instrumented_tree)
        
        # Generate the instrumented code
        instrumented_code = compile(instrumented_tree, filename=str(file_path), mode='exec')
        
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create a new file with the instrumented code
        output_file = Path(self.output_dir) / file_path.name
        with open(output_file, 'w') as f:
            f.write(ast.unparse(instrumented_tree))
        
        return str(output_file), instrumenter.get_instrumented_line_numbers()
    
    def run_instrumented_file(self, instrumented_file):
        """Run an instrumented file"""
        # First make sure our coverage tracker is available
        with open(f"{self.output_dir}/coverage_tracker.py", 'w') as f:
            f.write("""
import json
import atexit

class CoverageTracker:
    \"\"\"Singleton class to track coverage during program execution\"\"\"
    _instance = None
    _coverage_data = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoverageTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        \"\"\"Initialize the coverage tracker\"\"\"
        self._coverage_data = {}
        # Register the save method to run when Python exits
        atexit.register(self.save_coverage_data)
        
    def mark_line(self, filename, line_number):
        \"\"\"Mark a line as executed\"\"\"
        if filename not in self._coverage_data:
            self._coverage_data[filename] = {}
        
        self._coverage_data[filename][line_number] = self._coverage_data[filename].get(line_number, 0) + 1
    
    def save_coverage_data(self, output_file=".coverage_data.json"):
        \"\"\"Save coverage data to a file\"\"\"
        with open(output_file, 'w') as f:
            json.dump(self._coverage_data, f, indent=2)
        print(f"Coverage data saved to {output_file}")
    
    def get_coverage_data(self):
        \"\"\"Get the current coverage data\"\"\"
        return self._coverage_data

# Create a global instance that will be imported
_coverage_tracker = CoverageTracker()
""")
        
        # Also create a __init__.py in the output directory so it's treated as a package
        with open(f"{self.output_dir}/__init__.py", 'w') as f:
            f.write("# Package initialization file")
        
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
    
    def generate_report(self, source_file, coverage_data, instrumented_lines):
        """Generate a simple coverage report"""
        # Read the source file
        with open(source_file, 'r') as f:
            source_lines = f.readlines()
        
        # Get the coverage information
        file_coverage = coverage_data.get(str(source_file), {})
        
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


def main():
    """Main function to demonstrate the POC"""
    if len(sys.argv) < 2:
        print("Usage: python coverage_poc.py <python_file_to_instrument>")
        return
    
    source_file = sys.argv[1]
    
    # Create our coverage POC
    coverage_poc = Coverage()
    
    # Clean up previous output directory if it exists
    output_dir = ".coverage_instrumented"
    if os.path.exists(output_dir):
        import shutil
        print(f"Cleaning up previous instrumentation directory: {output_dir}")
        shutil.rmtree(output_dir, ignore_errors=True)
    
    # Instrument the file
    print(f"Instrumenting {source_file}...")
    instrumented_file, instrumented_lines = coverage_poc.instrument_file(source_file)
    print(f"File instrumented: {instrumented_file}")
    
    # Run the instrumented file
    print("Running instrumented file...")
    try:
        coverage_data = coverage_poc.run_instrumented_file(instrumented_file)
        
        # Generate and print the report
        report = coverage_poc.generate_report(source_file, coverage_data, instrumented_lines)
        print("\n" + report)
    except Exception as e:
        print(f"Error during execution: {e}")
        print("\nDebugging information:")
        print(f"- Check if '{output_dir}/coverage_tracker.py' exists and contains '_coverage_tracker' definition")
        print(f"- Verify imports in the instrumented file: {instrumented_file}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
