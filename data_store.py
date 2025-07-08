import os
import redis
import json
from dotenv import load_dotenv

load_dotenv()

r = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)

# ---------- Survey ----------
def get_all_surveys():
    keys = r.keys("survey:*")
    return [json.loads(r.get(k)) for k in keys]

def get_survey(sid):
    data = r.get(f"survey:{sid}")
    return json.loads(data) if data else None

def save_survey(survey: dict):
    r.set(f"survey:{survey['id']}", json.dumps(survey))

def delete_survey(sid):
    r.delete(f"survey:{sid}")
    r.delete(f"answers:{sid}")

# ---------- Answers ----------
def get_answers(sid):
    key = f"answers:{sid}"
    return [json.loads(v) for v in r.lrange(key, 0, -1)]

def get_all_answers():
    result = []
    for k in r.scan_iter("answers:*"):
        sid = k.split(":")[1]
        for val in r.lrange(k, 0, -1):
            answer = json.loads(val)
            answer["survey_id"] = sid
            result.append(answer)
    return result

def submit_answer(sid, user_id, answers):
    key = f"answers:{sid}"
    answer = {
        "user_id": user_id,
        "answers": answers
    }
    r.rpush(key, json.dumps(answer))

# ---------- Teachers ----------
def get_all_teachers():
    return [json.loads(r.get(k)) for k in r.keys("teacher:*")]

def get_teacher(username):
    data = r.get(f"teacher:{username}")
    return json.loads(data) if data else None

def save_teacher(username, password):
    r.set(f"teacher:{username}", json.dumps({
        "username": username,
        "password": password
    }))

def delete_teacher(username):
    r.delete(f"teacher:{username}")
