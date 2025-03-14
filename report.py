import json
import sys
import os
from pathlib import Path

from color import Colors

def generate_colored_report(source_file, coverage_data, use_colors=True):
    """
    컬러를 적용한 커버리지 보고서 생성
    """
    # 원본 소스 파일 읽기
    with open(source_file, 'r') as f:
        source_lines = f.readlines()
    
    # coverage_data에서 실행된 라인 번호 추출
    file_coverage = {}
    for filename, lines in coverage_data.items():
        # 단순 파일명만 비교 (경로 제외)
        if Path(filename).name == Path(source_file).name:
            file_coverage = lines
            break
    
    # 문자열 키를 정수로 변환
    file_coverage = {int(k): v for k, v in file_coverage.items()}
    executed_lines = set(file_coverage.keys())
    
    # 모든 라인을 계측 가능한 라인으로 간주 (보수적인 접근)
    all_lines = set(range(1, len(source_lines) + 1))
    
    # 문법적으로 실행 불가능한 라인 제외 (간단한 휴리스틱)
    non_executable_lines = set()
    for i, line in enumerate(source_lines, 1):
        line = line.strip()
        # 빈 줄, 주석, 문자열 리터럴, 함수/클래스 정의 등은 제외
        if (not line or 
            line.startswith('#') or 
            line.startswith('"""') or line.startswith("'''") or
            (line.startswith('def ') and line.endswith(':')) or
            (line.startswith('class ') and line.endswith(':'))):
            non_executable_lines.add(i)
    
    # 실행 가능한 라인들
    instrumented_lines = all_lines - non_executable_lines
    
    # 커버리지 백분율 계산
    if not instrumented_lines:
        coverage_percent = 0
    else:
        coverage_percent = (len(executed_lines.intersection(instrumented_lines)) / 
                          len(instrumented_lines)) * 100
    
    # 보고서 헤더 생성
    c = Colors if use_colors else type('NoColors', (), {k: '' for k in dir(Colors) if not k.startswith('__')})
    
    header = [
        f"{c.BOLD}{c.BRIGHT_CYAN}Coverage Report for {source_file}{c.RESET}",
        f"Total lines: {len(source_lines)}",
        f"Instrumented lines: {c.BOLD}{len(instrumented_lines)}{c.RESET}",
        f"Executed lines: {c.BOLD}{len(executed_lines)}{c.RESET}",
    ]
    
    # 커버리지 비율에 따른 색상 적용
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
    
    # 라인별 커버리지 정보 추가
    line_reports = []
    for i, line in enumerate(source_lines, 1):
        line_text = line.rstrip()
        
        if i in instrumented_lines:
            if i in executed_lines:
                count = file_coverage.get(i, 0)
                status = f"[{c.BRIGHT_GREEN}COVERED: {count}{c.RESET}]"
                line_num = f"{c.GREEN}{i:4d}{c.RESET}"
                
                # 실행된 라인 하이라이트
                if use_colors:
                    line_text = f"{c.WHITE}{line_text}{c.RESET}"
            else:
                status = f"[{c.BRIGHT_RED}NOT COVERED{c.RESET}]"
                line_num = f"{c.RED}{i:4d}{c.RESET}"
                
                # 실행되지 않은 라인 하이라이트
                if use_colors:
                    line_text = f"{c.BRIGHT_BLACK}{line_text}{c.RESET}"
        else:
            status = f"[{c.BRIGHT_BLACK}NOT INSTRUMENTED{c.RESET}]"
            line_num = f"{c.BRIGHT_BLACK}{i:4d}{c.RESET}"
            
            # 계측되지 않은 라인
            if use_colors:
                line_text = f"{c.BRIGHT_BLACK}{line_text}{c.RESET}"
        
        line_reports.append(f"{line_num} {status:40s} {line_text}")
    
    # 최종 보고서 조합
    return "\n".join(header + line_reports)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='컬러 터미널 지원 커버리지 보고서 생성기')
    parser.add_argument('source_file', help='분석할 원본 파이썬 파일')
    parser.add_argument('--no-color', action='store_true', help='컬러 출력 비활성화')
    parser.add_argument('--data-file', help='커버리지 데이터 JSON 파일 위치')
    args = parser.parse_args()
    
    source_file = args.source_file
    
    # 커버리지 데이터 파일 찾기
    if args.data_file:
        coverage_data_file = args.data_file
    else:
        # 기본 위치에서 검색
        coverage_data_file = ".coverage_instrumented/.coverage_data.json"
        if not os.path.exists(coverage_data_file):
            # 현재 디렉토리에서도 찾아봄
            coverage_data_file = ".coverage_data.json"
            if not os.path.exists(coverage_data_file):
                print("커버리지 데이터 파일을 찾을 수 없습니다.")
                sys.exit(1)
    
    # 커버리지 데이터 로드
    try:
        with open(coverage_data_file, "r") as f:
            coverage_data = json.load(f)
    except Exception as e:
        print(f"커버리지 데이터 로드 중 오류: {e}")
        sys.exit(1)
    
    # 컬러 사용 여부 확인 (환경 변수 확인)
    use_colors = not args.no_color and sys.stdout.isatty() and os.environ.get('TERM') not in ['dumb', 'unknown']
    
    # 보고서 생성 및 출력
    report = generate_colored_report(source_file, coverage_data, use_colors)
    print(report)


if __name__ == "__main__":
    main()
