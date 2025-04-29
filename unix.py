import requests
from datetime import datetime, timezone, timedelta
import json
from pprint import pprint
base_url = "https://uni-x.almv.kz"


def formatTime(new_time: datetime):
    time = new_time.isoformat().replace("+00:00", "Z")
    return time


def load_local_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


class Unix:
    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.token = self.get_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }

    def get_token(self):
        login_data = {
            "login": self.login,
            "password": self.password
        }
        d = requests.post(url=f"{base_url}/api/auth/login/", data=login_data)
        return d.json().get("token")

    def get_modules(self) -> list:
        courses = requests.get(
            url=f"{base_url}/api/modules/", headers=self.headers).json().get("modules")[1].get("courses")

        return list(map(lambda course: f"{course.get('id')}: {course.get('title')}", courses))

    def get_module_topics(self, module_id: int) -> dict:
        topics = requests.get(
            url=f"{base_url}/api/courses/{module_id}", headers=self.headers).json().get("topics")

        return list(map(lambda topic: {
            "title": topic.get("title"),
            "id": topic.get("id"),
            "lessons": list(map(lambda lesson: {
                "duration": lesson.get("videoDurationEn"),
                "title": lesson.get("title"),
                "id": lesson.get("id")
            }, topic.get("lessons")))
        }, topics))


    def start_quiz(self, quiz_id: int) -> dict:
        endpoint = f"{base_url}/api/quizes-start-time/"
        requests.post(url=endpoint, headers=self.headers, json={
          "quizId": 7692
        })

    def watch_video(self, lesson_id, duration) -> None:
        csrf_url = f"{base_url}/api/validates/csrf"

        browser_headers = {
            'Authorization': f"Bearer {self.token}",
            'Origin': 'https://uni-x.almv.kz',
            'Referer': f'https://uni-x.almv.kz/platform/lessons/{lesson_id}',
        }

        # Get CSRF token
        csrf_response = requests.post(csrf_url, headers=browser_headers, json={})

        if csrf_response.status_code != 201:
            print(f"Failed to get CSRF token. Status code: {csrf_response.status_code}")
            print(f"Response: {csrf_response.text}")
            return

        csrf_token = None

        for cookie in csrf_response.cookies:
            if cookie.name == 'XSRF-Token':
                csrf_token = cookie.value
                break


        validation_endpoint = f"{base_url}/api/validates/watched/"
        now = datetime.now(timezone.utc)

        cookies = {'XSRF-Token': csrf_token}

        start_data = {
            "event": "video-start",
            "lessonId": lesson_id,
            "currentSpeed": 1,
            "clientTimestamp": formatTime(now),
            "lang": "EN"
        }
        start_res = requests.post(
            url=validation_endpoint,
            headers=browser_headers,
            cookies=cookies,
            json=start_data
        )

        if start_res.status_code != 200 and start_res.status_code != 201:
            print(f"Failed at video-start. Status code: {start_res.status_code}")
            print(f"Response: {start_res.text}")
            return

        # Video reached event
        reach_data = {
            "event": "reached",
            "lessonId": lesson_id,
            "currentSpeed": 1,
            "clientTimestamp": formatTime(now + timedelta(seconds=duration)),
            "token": start_res.json().get("token"),
            "lang": "EN"
        }
        reach_res = requests.post(
            url=validation_endpoint,
            headers=browser_headers,
            cookies=cookies,
            json=reach_data
        )

        if reach_res.status_code != 200 and reach_res.status_code != 201:
            print(f"Failed at reached event. Status code: {reach_res.status_code}")
            print(f"Response: {reach_res.text}")
            return

        # Video end event
        end_data = {
            "event": "video-end",
            "lessonId": lesson_id,
            "currentSpeed": 1,
            "clientTimestamp": formatTime(now + timedelta(seconds=duration)),
            "lang": "EN",
            "token": reach_res.json().get("token")
        }
        end_res = requests.post(
            url=validation_endpoint,
            headers=browser_headers,
            cookies=cookies,
            json=end_data
        )

        if end_res.status_code != 200 and end_res.status_code != 201:
            print(f"Failed at video-end. Status code: {end_res.status_code}")
            print(f"Response: {end_res.text}")
            return

        watched_data = {
            "videoDuration": duration,
            "videoWatched": duration,
            "token": end_res.json().get("token"),
        }

        watched_url = f"{base_url}/api/lessons/{lesson_id}/watched"

        watched_response = requests.post(
            url=watched_url,
            headers=browser_headers,
            cookies=cookies,
            json=watched_data
        )

        if watched_response.status_code == 200 or watched_response.status_code == 201:
            print(f"Lesson {lesson_id} is watched")
        else:
            print(f"Failed to mark lesson {lesson_id} as watched. Status code: {watched_response.status_code}")
            print(f"Response: {watched_response.text}")

    def pass_quiz(self, lesson_id) -> None:
        # get quiz detail
        # quiz_detail = load_local_json("./2_quiz.json")
        quiz_endpoint = f"{base_url}/api/lessons/{lesson_id}/quiz/"
        quiz_detail = requests.get(url=quiz_endpoint, headers=u.headers).json()

        answers = []

        for question in quiz_detail.get("questions"):
            ans = [answer.get("id") for answer in question.get("answers")]
            answers.append({
                "questionId": question.get("id"),
                "allAnswersIds": ans,
                "userAnswersIds": [
                    ans[0]
                ],
                "isMultiple": question.get("isMultiple", False)
            })

        # check
        # check_res = load_local_json("./2.json")
        quiz_id = quiz_detail.get("id")

        self.start_quiz(quiz_id=quiz_id)

        check_endpoint = f"{base_url}/api/quizes/{quiz_id}/check"
        check_res = requests.get(url=check_endpoint, headers=u.headers, json={
            "answers": answers
        }).json()

        answers = []
        for question in check_res.get("history"):
            anses = [answer.get("id") for answer in question.get("answers")]
            answers.append({
                "questionId": question.get("id"),
                "allAnswersIds": anses,
                "userAnswersIds": [
                    next((ans.get("id") for ans in question.get("answers") if ans.get("isCorrect")), None)
                ],
                "isMultiple": question.get("isMultiple", False)
            })

        requests.get(url=check_endpoint, headers=u.headers, json={
            "answers": answers
        }).json()


if __name__ == "__main__":
    u = Unix("di_tleuzhanuly@kbtu.kz", "")
    # pprint(u.get_modules())
    # pprint(u.get_module_topics(module_id=266))

    u.watch_video(lesson_id=10360, duration=298)
    # u.pass_quiz(lesson_id=10263)
