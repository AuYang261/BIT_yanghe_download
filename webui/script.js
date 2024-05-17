document.getElementById("newTaskButton").onclick = function () {
  document.getElementById("taskPopup").style.display = "block";
};

document.getElementsByClassName("close")[0].onclick = function () {
  document.getElementById("taskPopup").style.display = "none";
};

window.onclick = function (event) {
  if (event.target === document.getElementById("taskPopup")) {
    document.getElementById("taskPopup").style.display = "none";
  }
};

// Implement the logic to fetch course number and handle form submission
function fetchCourseNumber() {
  fetch(`/get_course?course_id=${document.getElementById("courseId").value}`)
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      document.getElementById("courseList").innerHTML = ``;
      document.getElementById("courseName11").innerHTML = `课程名: <b>${
        data.courseName == "" ? "未知" : data.courseName
      }</b>`;
      document.getElementById("professor11").innerHTML = `老师: <b>${
        data.professor == "" ? "未知" : data.professor
      }</b>`;
      let courseListHTML = "";
      for (let i = 0; i < data.videoList.length; i++) {
        courseListHTML += `<li data-value="${i}">${data.videoList[i].title}</li>`;
      }
      document.getElementById("courseList").innerHTML = courseListHTML;
      document.querySelectorAll("#courseList li").forEach((item) => {
        item.addEventListener("click", () => {
          item.classList.toggle("selected");
        });
      });
    })
    .catch((error) => console.error("Error:", error));
}

document.getElementById("taskForm").onsubmit = function (event) {
  event.preventDefault();
  let courseId = document.getElementById("courseId").value;
  if (courseId.trim() == "") {
    alert("课程名不能为空");
    return;
  }
  let downloadType = document.getElementById("downloadType").value;
  let selected_index = [];
  let courseList = document.getElementById("courseList");
  for (let i = 0; i < courseList.childNodes.length; i++) {
    let child = courseList.childNodes[i];
    if (child.className == "selected") {
      selected_index.push(child.getAttribute("data-value"));
    }
  }
  let course_number = selected_index.join(",");
  fetch("/new_task", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      course_id: courseId.trim(),
      course_number: course_number,
      download_version: downloadType,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      document.getElementById("taskPopup").style.display = "none";
    })
    .catch((error) => console.error("Error:", error));
};

function getDownloadStatusText(task_obj) {
  const merge_status = task_obj["merge_status"];
  const cur = task_obj["cur"];
  const tot = task_obj["tot"];
  const cancel = task_obj["canceled"];
  if (cancel) {
    return "已取消";
  }
  if (merge_status == 0) {
    if (cur == 0) {
      return "等待中...";
    } else {
      return `下载中...(${((cur / tot) * 100).toFixed(2)} %)`;
    }
  } else if (merge_status == 1) {
    return "合并视频中...";
  } else if (merge_status == 2) {
    return "已完成";
  } else {
    return "未知状态";
  }
}

function cancelTask(btn) {
  let uuid = btn.getAttribute("data-task-uuid");
  console.log(uuid);
  fetch(`/kill_task?uuid=${uuid}`)
    .then((response) => response.json())
    .then((data) => console.log(data))
    .catch((error) => console.error("Error:", error));
}

setInterval(() => {
  const addElement = (task_obj) => {
    if (task_obj["canceled"]) {
      return;
    }
    const html = `
      <div class="task" id="${task_obj["uuid"]}-task">
        <div class="task-info">
          <span>${task_obj["name"]}</span>
          <div class="status-container">
            <span class="status" id="${
              task_obj["uuid"]
            }-status">${getDownloadStatusText(task_obj)}</span>
            <button class="cancel-btn" data-task-uuid="${
              task_obj["uuid"]
            }" onclick="cancelTask(this);">×</button>
          </div>
        </div>
        <div class="progress-bar">
          <div class="progress" id="${task_obj["uuid"]}-progress"></div>
        </div>
      </div>
    `;
    document.getElementById("taskList").innerHTML += html;
  };
  const updateElement = (task_obj) => {
    const uuid = task_obj["uuid"];
    const status_ele = document.getElementById(`${task_obj["uuid"]}-status`);
    const progress_ele = document.getElementById(
      `${task_obj["uuid"]}-progress`
    );
    status_ele.innerText = getDownloadStatusText(task_obj);
    const progress = (100 * task_obj["cur"]) / task_obj["tot"];
    progress_ele.style.width = `${progress.toFixed(2)}%`;
  };
  fetch("/get_status")
    .then((response) => response.json())
    .then((data) => {
      // console.log(data);
      for (let i = 0; i < data.length; i++) {
        const uuid = data[i]["uuid"];
        let exist_ele = document.getElementById(`${uuid}-task`);
        if (exist_ele == null) {
          addElement(data[i]);
        } else {
          updateElement(data[i]);
        }
      }
    })
    .catch((error) => console.error("Error:", error));
}, 1000);

const listItems = document.querySelectorAll("#courseList li");
listItems.forEach((item) => {
  item.addEventListener("click", () => {
    item.classList.toggle("selected");
  });
});
