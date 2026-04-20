# 鍚庣璇存槑

鍚庣鎶€鏈爤锛?

- FastAPI
- SQLAlchemy
- SQLite

## 鐜瑕佹眰

- Python `3.12.x`

涓嶈浣跨敤 Python `3.14`銆傚綋鍓嶄緷璧栨爤鍦?Windows 涓嬩細瑙﹀彂 `pydantic-core` 婧愮爜鏋勫缓锛屽鍔?Rust 鍜岀紪璇戝伐鍏疯姹傦紝涓嶉€傚悎褰撳墠椤圭洰銆?

## 鎵嬪姩鍚姩鏂瑰紡

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

濡傞渶鎭㈠鐪熷疄鏁版嵁锛屽啀鍗曠嫭鎵ц锛?

```powershell
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\import_real_test_data.py
```

璇ヨ剼鏈細鍏堟彁绀洪闄╋紝骞惰姹傝緭鍏ュ浐瀹氱‘璁よ瘝鍚庯紝鎵嶄細娓呯悊鏃т笟鍔℃暟鎹苟閲嶆柊瀵煎叆鐪熷疄鏁版嵁銆?

## 鎺ㄨ崘鏂瑰紡

浼樺厛浣跨敤椤圭洰鏍圭洰褰曠殑鑴氭湰锛?

- `scripts/start_system.bat`

濡傛灉鐜缂哄け锛屽畠浼氳嚜鍔ㄨ皟鐢ㄥ垵濮嬪寲鑴氭湰銆?

## 鏁版嵁搴撹鏄?

寮€鍙戠幆澧冩暟鎹簱浣嶄簬锛?

- `backend/training.db`

褰撳墠鍒濆鍖栬剼鏈彧璐熻矗鍒涘缓/琛ラ綈鏁版嵁搴撶粨鏋勶紝涓嶄細娓呯┖宸叉湁鏁版嵁锛屼篃涓嶄細鑷姩瀵煎叆浠讳綍棰勭疆鏁版嵁銆?
## 涓婁紶鍓嶆鏌?

```powershell
python -m compileall backend\app
```

## Git Database Workflow

- `backend/training.db` is tracked in Git and is the shared backend data file.
- After changing athlete or test data, commit `backend/training.db` together with the related code or documentation changes.
- On a new computer, pull the latest repository so the latest `backend/training.db` is available locally.
- `scripts/init_db.py` and `scripts/init_system.bat` only create or align schema. They do not restore business data into an empty database.
- Do not make different database edits on multiple computers in parallel unless you are prepared to choose one side manually.
