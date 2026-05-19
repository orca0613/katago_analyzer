import requests

localhost = "http://localhost:8080"
api_url = "https://national-team-project-backend-593632018880.asia-northeast3.run.app"

# 백엔드에서 허용하는 Origin
allowed_origin = "https://opening-note.web.app"

# 요청 헤더에 Origin을 추가
headers = {
  "Origin": allowed_origin
}

def get_unanalyzed_sgf_data():
  url = f"{localhost}/sgf-data/get-unanalyzed"
  response = requests.get(url=url, headers=headers)
  status_code = response.status_code
  if status_code == 200:
    return response.json()
  return False


def save_analyzed_data(data, sgf_index):
  body = {
    "data": data,
    "sgfIndex": sgf_index
  }
  url = f"{localhost}/katago-analysis/save"
  response = requests.post(url=url, headers=headers, json=body)
  status_code = response.status_code
  if status_code == 200:
    return response.json()
  return False