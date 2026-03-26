# 快速开始

本指南面向首次使用者优化。如果你只做三件事，请先做这三步：

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
make setup
make doctor
make start
```

## 每条命令的作用

- `make setup`：创建 `.venv`、安装依赖，并在需要时从模板生成 `.env`
- `make doctor`：执行环境体检并输出修复建议
- `make start`：先运行 doctor，再在 `127.0.0.1:8001` 启动 API

启动成功后可访问：

- API 健康检查：`http://127.0.0.1:8001/health`
- Swagger 文档：`http://127.0.0.1:8001/docs`
- Panel 面板：`http://127.0.0.1:8001/panel`

## 常用操作

```bash
make help
make test-quick
PORT=8010 make start
```

## 手动模式（不使用 Makefile）

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py --port 8001
PYTHONPATH=src .venv/bin/python -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8001 --reload
```

## 故障排查

- 如果 doctor 在依赖项上显示 `FAIL`，请重新执行 `make setup`。
- 如果端口 `8001` 被占用，使用 `PORT=8010 make start`。
- 如果出现导入错误，请优先使用 `make start` 启动，以自动设置 `PYTHONPATH=src`。

## Admin UI 帮助

- 字段逐项填写指南：`docs/admin-view-field-guide.md`
