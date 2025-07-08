
# 微调查系统部署文档

本说明文档涵盖了该系统的环境搭建、测试方式、运维部署方案、系统架构说明及如何嵌入视频网站页面中弹出问卷。

---

## 环境搭建

1. 安装 Python（建议 3.9+）
2. 安装依赖：
   在项目文件夹中打开控制台，输入

   ```bash
   pip install -r requirements.txt
   ```

3. 安装并运行 Redis（Windows 环境）

- 访问：[https://github.com/tporadowski/redis/releases](https://github.com/tporadowski/redis/releases)

- 下载最新的 `.msi` 安装包；

- 双击下载好的`.msi`，启动安装程序；

- 安装完成后，进入安装文件夹，双击运行：

   ```bash
   redis-server.exe
   ```

---

## 系统测试（本地）

1. 启动服务：在项目文件夹中打开控制台，输入

   ```bash
   uvicorn webapp:app --reload
   ```

2. 打开浏览器访问：

   ```
   http://127.0.0.1:8000/login
   ```

3. 使用 `root` 账号登录： `username:root / pwd:root_pwd`

4. 在“教师账号管理”中新建一个教师用户。

5. 新开浏览器标签页，用刚刚创建的教师账号登录系统并创建一个问卷。

6. 返回管理员后台，获取其问卷 ID。

7. 打开 `example_site/surey_popup.js`，将下面这一行代码

    ```bash
    iframe.src = "http://localhost:8000/survey/05ae6a6b-1a2b-48a4-a2f6-10efef7728f6?user_id=" + encodeURIComponent(userId);
    ```

    中`survey/`后的问卷 ID 替换为实际问卷 ID。

8. 双击 `index.html` 输入任意学号并登录，点击“作答问卷”按钮，体验问卷答题流程。

9. 作答完成后，在教师控制台和管理员控制台都可以看到该条作答记录

---

## 运维部署（对接服务器如 <https://bdata.bnu.edu.cn）>

### 1. 将项目上传至服务器（Linux）

```bash
scp -r 微调查系统 user@your_server:/var/www/survey
```

### 2. 进入服务器后安装依赖

```bash
cd /var/www/survey
pip install -r requirements.txt
```

### 3. 启动 Redis 服务

编辑 `.env`：

```ini
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=3
```

> 若服务器中已有 Redis ，请替换为实际连接参数。

### 4. 后台启动服务

```bash
nohup uvicorn webapp:app --host 0.0.0.0 --port 8000 &
```

### 5. 配置 Nginx

编辑 `/etc/nginx/sites-available/survey` 添加：

```nginx
server {
    listen 80;
    server_name bdata.bnu.edu.cn;

    location /survey/ {
        proxy_pass http://127.0.0.1:8000/survey/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000/admin/;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
    }
}
```

然后执行：

```bash
sudo ln -s /etc/nginx/sites-available/survey /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 系统架构说明

- `webapp.py`: FastAPI 主路由逻辑
- `data_store.py`: 所有 Redis 存储逻辑封装
- `templates/`: Jinja2 前端页面模板
- `static/`: 静态文件如 CSS、JS
- `.env`: Redis 配置
- `example_site/`: 示例网站，用于嵌入式问卷弹窗测试

---

## 弹出问卷接口说明

只需在视频网站播放页的js脚本中添加如下 iframe：

```html
<iframe src="https://bdata.bnu.edu.cn/survey/{问卷ID}?user_id={用户ID}" width="100%" height="600px" frameborder="0"></iframe>
```

### 示例

```html
<iframe src="https://bdata.bnu.edu.cn/survey/abcd-efgh-1234?user_id=stu001" width="100%" height="600px"></iframe>
```

其中user_id可以调用你方的获取当前学生id的接口来实现自动填写
