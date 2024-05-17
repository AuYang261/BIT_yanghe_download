from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import m3u8dl
import sys
import json
import os
import cProfile
import time
import utils
from queue import Queue, Empty
import uuid
import threading
import ctypes
import multiprocessing

app = Flask(__name__, static_folder='webui')

"""
    {
        "url":
        "output":
        "name":
        "cur":
        "tot":
        "uuid":
        "canceled":
        "merge_status": 
        “download_type”
    }
"""
all_task_status = [

]


"""
    {
        "uuid"
    }
"""
task_queue = Queue()


def find_all_task_by_uuid(uuid):
    for id, task in enumerate(all_task_status):
        if task["uuid"] == uuid:
            return task, id
    return None

g_father_queue = None
current_task_uuid = ""
def executor_progress_callback(cur, tot, merge_status):
    global g_father_queue, current_task_uuid
    g_father_queue.put({
        "uuid": current_task_uuid,
        "cur": cur,
        "tot": tot,
        "merge_status": merge_status
    })
    # print({
    #     "uuid": current_task_uuid,
    #     "cur": cur,
    #     "tot": tot,
    #     "merge_status": merge_status
    # })
    return False


def execute_one_download_task_worker(task_dict, father_queue):
    global current_task_uuid, g_father_queue
    print(f"downloading task {task_dict}")
    current_task_uuid = task_dict["uuid"]
    uuid = task_dict["uuid"]
    url = task_dict["url"]
    output = task_dict["output"]
    name = task_dict["name"]
    g_father_queue = father_queue
    m3u8dl.M3u8Download(
        url,
        output,
        name,
        progress_callback=executor_progress_callback
    )
    return

def execute_tasks():
    global all_task_status
    queue = multiprocessing.Queue()
    while True:
        try:
            task = task_queue.get(timeout=1)
            task_uuid = task["uuid"]
            task_obj, task_id = find_all_task_by_uuid(task_uuid)
            if task_obj["canceled"] == True:
                all_task_status.pop(task_id)
                continue
            process = multiprocessing.Process(target=execute_one_download_task_worker, args=(task_obj, queue))
            process.start()
            while True:
                if all_task_status[task_id]["canceled"]:
                    print("task canceled, terminate subprocess...")
                    process.terminate()
                    all_task_status.pop(task_id)
                    break
                try:
                    msg = queue.get_nowait()
                    update_obj, update_id = find_all_task_by_uuid(msg["uuid"])
                    all_task_status[update_id]["cur"] = msg["cur"]
                    all_task_status[update_id]["tot"] = msg["tot"]
                    all_task_status[update_id]["merge_status"] = msg["merge_status"]
                except Empty:
                    if process.is_alive() == False:
                        break
                    time.sleep(0.1)
                    continue
        except Empty:
            continue

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/get_course')
def get_course():
    course_id = request.args.get('course_id')
    try:
        videoList, courseName, professor = utils.get_course_info(courseID=course_id)
    except:
        return jsonify({
            "videoList": [],
            "courseName": "",
            "professor": ""
        })
    return jsonify({
        "videoList": videoList,
        "courseName": courseName,
        "professor": professor
    })

@app.route('/new_task', methods=['POST'])
def new_task():
    global task_queue, all_task_status
    data = request.json
    course_id = data['course_id']
    course_number = data['course_number']
    download_version = data['download_version']
    videoList, courseName, professor = utils.get_course_info(courseID=course_id)
    course_number_arr = course_number.split(",")
    ret_id = []
    for courseNum in course_number_arr:
        courseNumT = int(courseNum)
        c = videoList[courseNumT]
        name = courseName + "-" + professor + "-" + c["title"]
        print(name)

        cur_uuid = str(uuid.uuid4())
        ret_id.append(cur_uuid)
        task_status = {
            "url": "",
            "output": "",
            "name": name,
            "cur": 0,
            "tot": 0,
            "uuid": cur_uuid,
            "canceled": False,
            "merge_status": 0,
            "download_type": download_version
        }

        if download_version == "2":
            print("Downloading screen...")
            task_status["url"] = c["videos"][0]["vga"]
            task_status["output"] = "output/" + courseName + "-screen"
        else:
            print("Downloading video...")
            task_status["url"] = c["videos"][0]["main"]
            task_status["output"] = "output/" + courseName + "-video"
        all_task_status.append(task_status)
        task_queue.put({
            "uuid": cur_uuid
        })

    return jsonify({"status": "success", "task_id": ret_id})

@app.route('/get_status')
def get_status():
    global all_task_status
    return jsonify(all_task_status)

@app.route('/kill_task')
def kill_task():
    global all_task_status
    uuid = request.args.get('uuid')
    task, id = find_all_task_by_uuid(uuid)
    if task["merge_status"] == 2:
        # if already finished
        all_task_status.pop(id)
        return jsonify({"status": "ok"})
    all_task_status[id]["canceled"] = True
    return jsonify({"status": "ok"})

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    t = threading.Thread(target=execute_tasks)
    t.start()
    app.run(debug=False,host='0.0.0.0', use_reloader=False, port=5001)