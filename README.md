# 浣撹兘璁粌绠＄悊骞冲彴 V1

杩欐槸涓€涓互 `iPad / 骞虫澘妯睆` 涓轰富瑕佷娇鐢ㄥ満鏅殑浣撹兘璁粌绠＄悊骞冲彴锛岄潰鍚戝洟闃熻缁冪鐞嗐€佽缁冩墽琛屽拰璁粌鏁版嵁杩借釜銆?

褰撳墠鐗堟湰宸茬粡鎵撻€氫互涓嬩富娴佺▼锛?

- 鍔ㄤ綔搴撶鐞?
- 璁粌妯℃澘绠＄悊
- 璁″垝鍒嗛厤涓庡垎閰嶆€昏
- 璁粌妯″紡鎵ц
- 鑷姩璋冮噸寤鸿
- 娴嬭瘯鏁版嵁璁板綍
- 璁粌鏁版嵁鏌ョ湅
- Windows 涓€閿垵濮嬪寲涓庝竴閿惎鍔?
- iPad / PWA 鍩虹鏀寔
- 鍗曞叆鍙ｅ惎鍔?+ 鍙充笂瑙掓ā寮忓垏鎹?

## 褰撳墠浣跨敤鏂瑰紡

绯荤粺鐩墠閲囩敤 **鍏嶇櫥褰曟ā寮?*锛?

- 鎵撳紑绯荤粺鍚庨粯璁よ繘鍏?**璁粌妯″紡**
- 鍙充笂瑙掑彲鍒囨崲鍒?**绠＄悊妯″紡**
- 绯荤粺浼氳浣忎笂娆′娇鐢ㄧ殑妯″紡
- 涓嶉渶瑕佽緭鍏ヨ处鍙峰瘑鐮?

## 鐜瑕佹眰

璇峰厛瀹夎浠ヤ笅杞欢锛?

- Python `3.12.x`
- Node.js `18+`
- Git

寤鸿瀹夎鏃堕兘鍕鹃€夊姞鍏?PATH銆?

## 鏈湴鍚姩

### 鏈€绠€鍗曟柟寮?

骞虫椂鍙渶瑕佸弻鍑伙細

- `scripts/start_system.bat`

杩欎釜鑴氭湰浼氳嚜鍔ㄥ垽鏂槸鍚︾己灏戠幆澧冩垨渚濊禆锛?

- 濡傛灉鏄涓€娆¤繍琛岋紝浼氳嚜鍔ㄦ墽琛屽垵濮嬪寲
- 鍒濆鍖栧畬鎴愬悗浼氱户缁惎鍔ㄥ墠鍚庣
- 鐒跺悗鑷姩鎵撳紑娴忚鍣?
- 鍒濆鍖栧彧浼氬垱寤?琛ラ綈鏁版嵁搴撶粨鏋勶紝涓嶄細娓呯┖宸叉湁鏁版嵁

### 鍒濆鍖栬剼鏈?

濡傛灉浣犻渶瑕佹墜鍔ㄩ噸瑁呯幆澧冿紝鍙互鍗曠嫭鍙屽嚮锛?

- `scripts/init_system.bat`

瀹冧細鑷姩瀹屾垚锛?

- 妫€鏌?Python / Node.js / npm
- 鍒涘缓鍚庣铏氭嫙鐜
- 瀹夎鍚庣渚濊禆
- 鍒涘缓鎴栬ˉ榻愭暟鎹簱缁撴瀯
- 瀹夎鍓嶇渚濊禆

濡傛灉浣犻渶瑕佹仮澶嶇湡瀹為槦浼嶆暟鎹紝璇烽澶栨墽琛岋細

- `backend/scripts/import_real_test_data.py`
- 璇ヨ剼鏈細鍏堣姹傝緭鍏ュ浐瀹氱‘璁よ瘝锛岀‘璁ゅ悗鎵嶄細娓呯悊鏃т笟鍔℃暟鎹苟閲嶆柊瀵煎叆

## iPad 璁块棶鏂瑰紡

璇风‘璁わ細

- iPad 鍜岀數鑴戣繛鎺ュ湪鍚屼竴涓?Wi-Fi
- 鐢佃剳宸茬粡杩愯 `scripts/start_system.bat`

鐒跺悗鍦?iPad Safari 涓墦寮€锛?

```text
http://浣犵殑鐢佃剳IPv4鍦板潃:5173
```

渚嬪锛?

```text
http://192.168.1.25:5173
```

## 娣诲姞鍒?iPad 涓诲睆骞?

1. 鐢?Safari 鎵撳紑绯荤粺棣栭〉
2. 鐐瑰嚮鈥滃垎浜€?
3. 閫夋嫨鈥滄坊鍔犲埌涓诲睆骞曗€?
4. 鍥炲埌涓诲睆骞曞悗鐐瑰嚮鍥炬爣鍗冲彲鍍?App 涓€鏍锋墦寮€

## 鐩綍缁撴瀯

```text
backend/    鍚庣鏈嶅姟銆佹暟鎹簱銆佷笟鍔￠€昏緫銆佸垵濮嬪寲鑴氭湰
frontend/   鍓嶇椤甸潰銆佺粍浠躲€佺姸鎬佺鐞嗐€丳WA 璧勬簮
scripts/    Windows 涓€閿垵濮嬪寲涓庡惎鍔ㄨ剼鏈?
```

## GitHub 涓婁紶娴佺▼

### 绗竴姝ワ細瀹夎 Git

瀹夎瀹屾垚鍚庯紝鍦ㄧ粓绔墽琛岋細

```powershell
git --version
```

濡傛灉鑳界湅鍒扮増鏈彿锛屽氨璇存槑 Git 鍙敤銆?

### 绗簩姝ワ細鍦?GitHub 鏂板缓绉佹湁浠撳簱

寤鸿锛?

- 鏂板缓 **绉佹湁浠撳簱**
- 鍒涘缓鏃朵笉瑕佸嬀閫夎嚜鍔ㄧ敓鎴?README

### 绗笁姝ワ細鏈湴涓婁紶

鍦ㄩ」鐩牴鐩綍鎵ц锛?

```powershell
git init
git add .
git commit -m "鍒濆鍖栦綋鑳借缁冪鐞嗗钩鍙?V1"
git branch -M main
git remote add origin 浣犵殑浠撳簱鍦板潃
git push -u origin main
```

## 璺ㄧ數鑴戠户缁紑鍙?

鍦ㄦ柊鐢佃剳涓婏細

1. 瀹夎 Python 3.12銆丯ode.js銆丟it
2. 鍏嬮殕浠撳簱
3. 杩涘叆椤圭洰鐩綍
4. 鍙屽嚮 `scripts/start_system.bat`

濡傛灉鏂扮數鑴戣繕娌℃湁渚濊禆鐜锛岃剼鏈細鑷姩鍒濆鍖栥€?

## 鍗忎綔鏂囨。

涓轰簡璁╁叾浠栧紑鍙戣€呮垨鍏朵粬 AI / vibe coding 宸ュ叿蹇€熸帴鎵嬶紝杩欎釜浠撳簱搴斿悓鏃剁淮鎶わ細

- `PROJECT_CONTEXT.md`
- `DEVELOPMENT_GUIDE.md`

瀹冧滑鍒嗗埆璐熻矗锛?

- 椤圭洰鑳屾櫙銆佸姛鑳借竟鐣屻€佸綋鍓嶆灦鏋勩€佷笟鍔¤鍒?
- 缂栫爜瑙勮寖銆佹敼鍔ㄥ師鍒欍€佹ā鍧楀垎灞傘€侀獙璇佽姹?

## 涓婁紶鍓嶆鏌?

涓婁紶鍒?GitHub 鍓嶏紝寤鸿鑷冲皯纭锛?

```powershell
cd frontend
npm run build
```

```powershell
cd ..
python -m compileall backend\app
```

骞剁‘璁わ細

- `README.md` 涓嶄贡鐮?
- 鍒濆鍖栦笉浼氭竻绌哄凡鏈夌湡瀹炴暟鎹?
- `scripts/start_system.bat` 鍙互鐩存帴鍚姩

## 甯歌闂

### 1. 鎵句笉鍒?Python

璇峰畨瑁?Python `3.12.x`锛屽苟纭锛?

```powershell
python --version
```

杈撳嚭搴斾负锛?

```text
Python 3.12.x
```

### 2. 鎵句笉鍒?Node.js 鎴?npm

璇峰畨瑁?Node.js `18+`锛岀劧鍚庨噸鏂版墦寮€缁堢锛屽啀鎵ц锛?

```powershell
node -v
npm -v
```

### 3. 鎵句笉鍒?Git

璇峰畨瑁?Git锛屽苟纭锛?

```powershell
git --version
```

### 4. 娴忚鍣ㄦ墦涓嶅紑椤甸潰

璇锋鏌ワ細

- 鍓嶇鏄惁杩愯鍦?`5173`
- 鍚庣鏄惁杩愯鍦?`8000`
- 鏄惁鏈夊叾浠栫▼搴忓崰鐢ㄤ簡绔彛

### 5. iPad 鎵撳緱寮€椤甸潰浣嗘病鏈夋暟鎹?

甯歌鍘熷洜锛?

- 鍚庣娌℃湁鎴愬姛鍚姩
- 鐢佃剳闃茬伀澧欐嫤鎴簡 `8000`
- iPad 鍜岀數鑴戜笉鍦ㄥ悓涓€涓?Wi-Fi

## GitHub Data Sync

- `backend/training.db` is the shared project database file and should be committed to Git.
- When switching to another computer, `git pull` the latest repo before starting the system.
- If you modify athlete or test data and want that data on another computer, commit and push `backend/training.db`.
- `scripts/init_system.bat` only ensures schema and dependencies. It does not restore business data.
- The shared business data source is the `backend/training.db` file stored in Git.
- Avoid editing the database on two computers at the same time. SQLite conflicts are not safely mergeable.

## 动作库数据源与导入

- 当前动作库的唯一权威数据源是 `C:\Users\tzy\Downloads\exos_action_library_tagged_for_codex.xlsx`
- 正式导入只读取 sheet `动作库_标签版`
- 关键字段来源：
  - `动作ID建议` -> `exercises.code`
  - `动作名称` -> `exercises.name`
  - `动作英文原名` -> `exercises.name_en`
  - `一级分类 / 二级分类 / 基础动作` -> 分类字段与 `exercise_categories`
  - 所有 `标签_...` 列 -> `exercises.structured_tags`
  - `标签_检索关键词` + 中文名 + 英文名 + 标签词条 + 分类路径 -> `exercises.search_keywords`
  - `标签词条` -> `exercises.tag_text`
  - `分类路径` -> `exercises.category_path`
- 动作库导入脚本：
  - `backend/scripts/import_exos_action_library.py --preview`
  - `backend/scripts/import_exos_action_library.py --apply --replace-existing`
- 导入结果会写入：
  - `exercise_categories`：一级分类、二级分类、基础动作
  - `exercises`：具体动作及结构化标签元数据
- 动作库页面支持：
  - 一级分类筛选
  - 二级分类联动筛选
  - 关键词搜索
  - 结构化标签筛选
  - 动作详情查看

## 动作库维护方式

- EXOS 动作库初始化导入已经完成，网页端不再提供 `导入预览` 或 `导入 Excel` 入口。
- 日常维护请直接使用网页端的：
  - 新建动作
  - 编辑动作
  - 删除动作
- 导入能力仅保留为维护级后备通道：
  - 后端导入 API
  - `backend/scripts/import_exos_action_library.py`
- 删除动作时会检查训练模板项和训练执行记录引用；存在引用时，系统会拒绝删除并提示先清理业务引用。

更多字段结构和导入规则见 `EXERCISE_LIBRARY_SPEC.md`。
