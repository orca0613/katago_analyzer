import asyncio
import json
import subprocess
import time
from typing import List

from api import get_unanalyzed_sgf_data, save_analyzed_data
from functions import convert_sequence_for_katago, extract_komi, get_katago_cmd, refine_response

def run_katago_analysis(cmd: List[str], input_json):
  analysis_data = []
  process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, 
    text=True,
    bufsize=1 # 라인 단위 버퍼링
  )
  try:
    print(f"🤖 {len(input_json)}개의 분석 데이터를 엔진에 주입 시작...")
    
    line = json.dumps(input_json, ensure_ascii=False) + "\n"
    process.stdin.write(line)
    process.stdin.flush()
    
    # ⚠️ 전송 직후 입력을 닫아도 카타고는 해당 쿼리 분석을 끝까지 수행합니다.
    process.stdin.close()

    # 4. 카타고가 내뱉는 결과를 실시간으로 읽고 정제하여 저장
    while True:
      output = process.stdout.readline()
      
      # 프로세스가 종료되고 더 이상 읽을 출력이 없으면 종료
      if not output and process.poll() is not None:
        break
      
      refined = refine_response(output)
      if not refined:
        continue
      
      # 정제된 한 줄의 JSON만 파일에 저장
      analysis_data.append(refined)
      
      # 진행 상황 출력 (예: . 대신 요약 정보 출력)
      print(f"\r{refined["turn"]}수 [분석 중]", end="", flush=True)

    process.wait()
    
    if process.returncode != 0:
      error_msg = process.stderr.read()
      print(f"\n❌ 분석 실패: {error_msg}")
    else:
      return analysis_data

  except Exception as e:
    print(f"\n❌ 프로세스 제어 오류: {e}")
    if process: process.kill()


async def main():
  visit_tests = 1000

  cmd = get_katago_cmd()
  if not cmd:
    return
  
  while True:
    try:
      sgf_data = get_unanalyzed_sgf_data() # API에서 기보 가져오기
      if not sgf_data:
        print("데이터가 없습니다.")
        return
      
      si = sgf_data.get("si")
      sgf = sgf_data.get("sgf")
      komi = extract_komi(sgf)
      moves = convert_sequence_for_katago(sgf_data.get("sequence"))
      
      request = {
        "id": str(si),
        "moves": moves,
        "komi": komi,
        "boardXSize": 19,
        "boardYSize": 19,
        "rules": "chinese" if komi == 7.5 else "japanese", # komi에 따라 변경 필요!!!
        "maxVisits": visit_tests,
        "analysisPVLen": 15,
        "includePolicy": False,  
        "includeOwnership": False, 
        "analyzeTurns": list(range(len(moves) + 1)) # 모든 수순 분석
      }

      # --- [2단계] 생성된 파일을 카타고에게 던지기 ---
      print(f"🤖 카타고 분석 시작 (이 작업은 엔진 성능을 풀로 사용합니다)...")
      start_time = time.time()
      
      # subprocess가 끝나야 다음 코드로 넘어갑니다.
      data = run_katago_analysis(cmd, request)
      data.sort(key=lambda x: x.get("turn"))
      response = save_analyzed_data(data, si)
      if not response.get("result"):
        break
      
      elapsed = time.time() - start_time
      print(f"✅ 분석 완료! 소요시간: {elapsed:.2f}s")


    except Exception as e:
      print(f"❌ 오류 발생: {e}")
      break


if __name__ == "__main__":
    asyncio.run(main())