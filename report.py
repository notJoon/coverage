import json
import sys
import os
from pathlib import Path

from color import Colors

def generate_colored_report(source_file, coverage_data, use_colors=True):
    # read source file
    with open(source_file, 'r') as f:
        source_lines = f.readlines()

    # extract executed lines from coverage_data json file
    file_coverage = coverage_data.get(source_file, {}).get('lines', {})
    file_coverage = {int(k): v for k, v in file_coverage.items()}
    executed_lines = set(file_coverage.keys())

    # consider all lines as instrumented lines (conservative approach)
    all_lines = set(range(1, len(source_lines) + 1))

    # exclude non-executable lines (simple heuristic)
    non_executable_lines = set()
    for i, line in enumerate(source_lines, 1):
        line = line.strip()
        # exclude empty lines, comments, string literals, function/class definitions, etc.
        if (not line or 
            line.startswith('#') or 
            line.startswith('"""') or line.startswith("'''") or
            (line.startswith('def ') and line.endswith(':')) or
            (line.startswith('class ') and line.endswith(':'))):
            non_executable_lines.add(i)
    
    # get executable lines
    instrumented_lines = all_lines - non_executable_lines

    # calculate coverage percentage
    if not instrumented_lines:
        coverage_percent = 0
    else:
        coverage_percent = (len(executed_lines.intersection(instrumented_lines)) / 
                          len(instrumented_lines)) * 100

    # generate report header
    c = Colors if use_colors else type('NoColors', (), {k: '' for k in dir(Colors) if not k.startswith('__')})

    header = [
        f"{c.BOLD}{c.BRIGHT_CYAN}Coverage Report for {source_file}{c.RESET}",
        f"Total lines: {len(source_lines)}",
        f"Instrumented lines: {c.BOLD}{len(instrumented_lines)}{c.RESET}",
        f"Executed lines: {c.BOLD}{len(executed_lines)}{c.RESET}",
    ]

    # apply color based on coverage percentage
    if coverage_percent >= 80:
        coverage_color = c.BRIGHT_GREEN
    elif coverage_percent >= 50:
        coverage_color = c.BRIGHT_YELLOW
    else:
        coverage_color = c.BRIGHT_RED
        
    header.append(f"Coverage: {c.BOLD}{coverage_color}{coverage_percent:.2f}%{c.RESET}")
    header.extend([
        f"\n{c.UNDERLINE}Line by line coverage:{c.RESET}",
        f"{c.BRIGHT_BLACK}{'=' * 70}{c.RESET}"
    ])

    # add line-by-line coverage information
    line_reports = []
    for i, line in enumerate(source_lines, 1):
        line_text = line.rstrip()

        if i in instrumented_lines:
            if i in executed_lines:
                count = file_coverage.get(i, 0)
                status = f"[{c.BRIGHT_GREEN}COVERED: {count}{c.RESET}]"
                line_num = f"{c.GREEN}{i:4d}{c.RESET}"
                
                # highlight executed lines
                if use_colors:
                    line_text = f"{c.WHITE}{line_text}{c.RESET}"
            else:
                status = f"[{c.BRIGHT_RED}NOT COVERED{c.RESET}]"
                line_num = f"{c.RED}{i:4d}{c.RESET}"

                # highlight unexecuted lines
                if use_colors:
                    line_text = f"{c.BRIGHT_BLACK}{line_text}{c.RESET}"
        else:
            status = f"[{c.BRIGHT_BLACK}NOT INSTRUMENTED{c.RESET}]"
            line_num = f"{c.BRIGHT_BLACK}{i:4d}{c.RESET}"
            
            # handle uninstrumented lines
            if use_colors:
                line_text = f"{c.BRIGHT_BLACK}{line_text}{c.RESET}"
        
        line_reports.append(f"{line_num} {status:40s} {line_text}")

    # combine final report
    return "\n".join(header + line_reports)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='color terminal supported coverage report generator')
    parser.add_argument('source_file', help='analyze source python file')
    parser.add_argument('--no-color', action='store_true', help='disable color output')
    parser.add_argument('--data-file', help='coverage data json file location')
    args = parser.parse_args()

    source_file = args.source_file

    # find coverage data file
    if args.data_file:
        coverage_data_file = args.data_file
    else:
        # search in default location
        coverage_data_file = ".coverage_instrumented/.coverage_data.json"
        if not os.path.exists(coverage_data_file):
            # search in current directory
            coverage_data_file = ".coverage_data.json"
            if not os.path.exists(coverage_data_file):
                print("coverage data file not found.")
                sys.exit(1)

    # load coverage data
    try:
        with open(coverage_data_file, "r") as f:
            coverage_data = json.load(f)
    except Exception as e:
        print(f"error loading coverage data: {e}")
        sys.exit(1)

    # check if color is enabled (check environment variable)
    use_colors = not args.no_color and sys.stdout.isatty() and os.environ.get('TERM') not in ['dumb', 'unknown']

    # generate report and print
    report = generate_colored_report(source_file, coverage_data, use_colors)
    print(report)


if __name__ == "__main__":
    main()
