from fastapi import FastAPI, Request, Form, Response, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from dotenv import load_dotenv
import os

from data_store import (
    get_all_surveys, get_survey, save_survey, delete_survey,
    get_answers, submit_answer, get_all_answers,
    get_teacher, save_teacher, delete_teacher, get_all_teachers
)

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def is_teacher(request: Request) -> bool:
    user = request.cookies.get("user")
    return user and user != "root"

def is_logged_in(request: Request) -> bool:
    return request.cookies.get("user") is not None

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "root" and password == "root_pwd":
        response = RedirectResponse("/admin/dashboard", status_code=302)
        response.set_cookie("user", "root", httponly=True)
        return response
    teacher = get_teacher(username)
    if teacher and teacher.get("password") == password:
        response = RedirectResponse("/teacher/surveys", status_code=302)
        response.set_cookie("user", username, httponly=True)
        return response
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "用户名或密码错误"
    })

@app.get("/admin/logout")
def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("user")
    return response

@app.get("/teacher/surveys")
def list_surveys(request: Request):
    user = request.cookies.get("user")
    if not is_teacher(request):
        return RedirectResponse("/login", status_code=302)

    surveys = get_all_surveys()
    if user != "root":
        surveys = [s for s in surveys if s.get("creator") == user]

    return templates.TemplateResponse("teacher_survey_list.html", {
        "request": request,
        "surveys": list(reversed(surveys))
    })

@app.get("/teacher/surveys/new")
def new_survey_page(request: Request):
    if not is_teacher(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("teacher_survey_new.html", {"request": request})

@app.post("/teacher/surveys/new")
async def create_survey_form(request: Request, title: str = Form(...), description: str = Form(...)):
    form = await request.form()
    questions = []

    for key in form:
        if key.startswith("q") and key.endswith("_content"):
            qid = key.split("_")[0]
            content = form[key]
            qtype = form.get(f"{qid}_type")
            options_raw = form.get(f"{qid}_options", "").strip()
            question = {
                "id": qid,
                "type": qtype,
                "content": content
            }
            if qtype in ["single", "multiple"]:
                options = [opt.strip() for opt in options_raw.split("\n") if opt.strip()]
                question["options"] = options
            questions.append(question)

    survey = {
        "id": str(uuid4()),
        "title": title,
        "description": description,
        "creator": request.cookies.get("user") or "unknown",
        "questions": questions
    }
    save_survey(survey)
    return RedirectResponse("/teacher/surveys", status_code=302)

@app.get("/teacher/surveys/detail/{survey_id}")
def view_survey_detail(survey_id: str, request: Request):
    user = request.cookies.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    survey = get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    answers = list(reversed(get_answers(survey_id)))
    statistics = []

    for q in survey["questions"]:
        qid = q["id"]
        result = {}
        if q["type"] in ["single", "multiple"]:
            for ans in answers:
                val = ans["answers"].get(qid)
                if isinstance(val, list):
                    for v in val:
                        result[v] = result.get(v, 0) + 1
                elif val is not None:
                    result[val] = result.get(val, 0) + 1
            stat_result = [{"label": q["options"][int(k)], "count": v} for k, v in result.items()]
        elif q["type"] == "true_false":
            count_true = sum(1 for ans in answers if ans["answers"].get(qid) is True)
            count_false = sum(1 for ans in answers if ans["answers"].get(qid) is False)
            stat_result = [{"label": "是", "count": count_true}, {"label": "否", "count": count_false}]
        elif q["type"] == "text":
            count = sum(1 for ans in answers if ans["answers"].get(qid))
            stat_result = {"count": count}
        else:
            stat_result = {}

        statistics.append({
            "id": qid,
            "content": q["content"],
            "type": q["type"],
            "result": stat_result if isinstance(stat_result, list) else [],
            "count": stat_result["count"] if isinstance(stat_result, dict) else None
        })

    return templates.TemplateResponse("teacher_survey_detail.html", {
        "request": request,
        "survey": survey,
        "answers": answers,
        "statistics": statistics
    })

@app.post("/teacher/surveys/delete/{survey_id}")
def delete_survey_route(survey_id: str, request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    delete_survey(survey_id)

    user = request.cookies.get("user")
    if user == "root":
        return RedirectResponse("/admin/dashboard", status_code=302)
    else:
        return RedirectResponse("/teacher/surveys", status_code=302)


@app.get("/teacher/surveys/preview/{survey_id}")
def preview_survey_info(survey_id: str, request: Request):
    survey = get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return templates.TemplateResponse("teacher_survey_preview.html", {
        "request": request,
        "survey": survey
    })

@app.get("/admin/dashboard")
def superadmin_dashboard(request: Request):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    surveys = get_all_surveys()
    teachers = get_all_teachers()

    survey_answer_stats = []
    total_answer_count = 0

    for s in surveys:
        answers = get_answers(s["id"])
        count = len(answers)
        total_answer_count += count
        survey_answer_stats.append({
            "id": s["id"],
            "title": s["title"],
            "count": count
        })

    top_survey_answers = sorted(survey_answer_stats, key=lambda x: x["count"], reverse=True)[:5]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "surveys": surveys,
        "teachers": teachers,
        "total_answer_count": total_answer_count,
        "top_survey_answers": top_survey_answers
    })

@app.get("/admin/teachers/new")
def add_teacher_page(request: Request):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("admin_teacher_new.html", {"request": request})

@app.post("/admin/teachers/new")
async def add_teacher_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    teachers = get_all_teachers()
    if any(t["username"] == username for t in teachers):
        return templates.TemplateResponse("admin_teacher_new.html", {
            "request": request,
            "error": "该用户名已存在"
        })

    teachers.append({"username": username, "password": password})
    save_teacher(username, password)
    return RedirectResponse("/admin/dashboard", status_code=302)

@app.post("/admin/teachers/delete/{username}")
def delete_teacher_handler(username: str, request: Request):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    delete_teacher(username)
    return RedirectResponse("/admin/dashboard", status_code=302)

@app.get("/admin/teachers/edit/{username}")
def edit_teacher_page(username: str, request: Request):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    teacher = get_teacher(username)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    return templates.TemplateResponse("admin_teacher_edit.html", {
        "request": request,
        "teacher": teacher
    })

@app.post("/admin/teachers/edit/{username}")
async def edit_teacher_submit(username: str, request: Request, password: str = Form(...)):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    teacher = get_teacher(username)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    save_teacher(username, password)
    return RedirectResponse("/admin/dashboard", status_code=302)

@app.get("/admin/answers/all")
def view_all_answers(request: Request):
    if request.cookies.get("user") != "root":
        return RedirectResponse("/login", status_code=302)

    surveys = get_all_surveys()
    survey_list = []

    for s in surveys:
        answers = get_answers(s["id"])
        count = len(answers)
        survey_list.append({
            "id": s["id"],
            "title": s["title"],
            "description": s.get("description", ""),
            "answer_count": count
        })

    return templates.TemplateResponse("admin_all_answers.html", {
        "request": request,
        "surveys": survey_list
    })

@app.get("/survey/{survey_id}")
def student_fill_page(survey_id: str, request: Request, user_id: str = Query(default="anonymous")):
    survey = get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    return templates.TemplateResponse("student_survey.html", {
        "request": request,
        "survey": survey,
        "user_id": user_id
    })

@app.post("/survey/{survey_id}")
async def student_submit_form(survey_id: str, request: Request):
    survey = get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    form = await request.form()
    user_id = form.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id 参数")

    answers = get_answers(survey_id)
    for ans in answers:
        if ans.get("user_id") == user_id:
            return JSONResponse({"message": "你已提交过该问卷"}, status_code=409)

    answers_dict = {}
    for q in survey["questions"]:
        qid = q["id"]
        if q["type"] == "multiple":
            answers_dict[qid] = [int(i) for i in form.getlist(qid)]
        elif q["type"] == "true_false":
            answers_dict[qid] = form.get(qid) == "true"
        elif q["type"] == "single":
            val = form.get(qid)
            answers_dict[qid] = int(val) if val else None
        elif q["type"] == "text":
            answers_dict[qid] = form.get(qid)

    submit_answer(survey_id, user_id, answers_dict)
    return JSONResponse({"message": "提交成功"})

@app.get("/api/survey/answered/{survey_id}")
def check_answered(survey_id: str, user_id: str):
    answers = get_answers(survey_id)
    for ans in answers:
        if ans.get("user_id") == user_id:
            return {"answered": True}
    return {"answered": False}
