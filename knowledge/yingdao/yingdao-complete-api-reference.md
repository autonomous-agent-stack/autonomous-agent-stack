# 影刀 RPA 完整 API 参考文档
> 研究基线：影刀帮助中心公开“开放 API”目录，共核验 44 个页面、35 个具备明确 HTTP 端点的接口页面。
> 核验日期：2026-03-24
> 使用方式：本稿优先给出“官方文档核验后的事实”，再给出集成侧的落地建议。对于需要人工在控制台完成的配置项（例如回调地址、API Key、任务编排），本文会明确标注。

## 1. 这次核验得到的关键结论
- 影刀开放 API 的“接口页”可以分成 10 个能力组：鉴权、RPA 企业账号、工作队列、任务运行、JOB 运行、运行日志、机器人相关、应用相关、文件、任务。
- 另有 3 类“运行约束页”：通用说明、限流与枚举、参考案例下载。这些页面不提供独立业务端点，但对企业集成是否稳定、是否可审计至关重要。
- 官方公开文档中，大多数端点以 `https://api.yingdao.com` 为公有云入口；而“任务”组 5 个接口的公开文档仍指向 `https://api.winrobot360.com`。这通常意味着文档仍保留旧域名或兼容域名。企业接入时应以自己租户的实际环境域名为准，并把该差异纳入环境配置。
- “任务运行(task/xxx)”与“JOB 运行(job/xxx)”是两个不同抽象层级：前者偏任务编排，后者偏单应用直接调度。错误地用 `taskUuid` 调 `job/stop` 或用 `jobUuid` 调 `task/query` 是官方 FAQ 中反复出现的问题。
- 影刀公开文档反复强调大参数治理：总输入参数建议不超过 8000 字符；超过阈值时，推荐先把内容转成文件，再通过“文件上传 + file 类型参数”传入。
- 企业级落地不应只做“启动接口调用”，而应同时设计好：回调、轮询、幂等、限流预算、机器人池容量、错误补偿、审计记录。

## 2. 模块总览
| 模块 | 页面数 | 具备端点的页面数 | 职责摘要 |
| --- | --- | --- | --- |
| RPA企业账号 | 5 | 5 | 负责企业调度账号的生命周期管理，适合对机器人执行账号进行集中创建、修改、密码重置和清理。 |
| 工作队列 | 4 | 4 | 把业务对象拆成队列项进行流式消费，是企业级削峰、异步解耦和失败补偿的关键模块。 |
| 任务运行 | 4 | 3 | 面向“任务/编排”模型，适合一个任务中包含多个应用与机器人关系、需要复杂调度编排的场景。 |
| JOB运行 | 6 | 5 | 面向“单应用 + 指定机器人/分组”的轻量调度模型，适合简单的一对一执行。 |
| 运行日志 | 3 | 3 | 提供日志搜索、通知式获取和轮询式获取三种手段，用于运行可观测性与故障排查。 |
| 机器人相关 | 4 | 4 | 提供机器人、机器人分组、机器人队列的查询能力，是调度器做资源选择和容量决策的基础。 |
| 应用相关 | 4 | 4 | 提供应用目录、应用运行记录、主流程参数结构和所有权转移能力，适合资产治理与变更管理。 |
| 文件 | 1 | 1 | 提供文件上传入口，可把长文本或大参数先转成文件，再通过 file 类型参数传入应用。 |
| 任务 | 5 | 5 | 提供调度记录、任务详情、最新执行记录和单任务执行明细，适合后台对账、审计和运维看板。 |
| 通用说明 | 6 | 0 | 涵盖限流、枚举、响应格式、参数类型和 FAQ，是所有企业集成前必须补齐的运行约束层。 |
| 参考案例下载 | 1 | 0 | 官方给出的 Postman、Java、Python、验签材料下载页，适合作为接入样板仓。 |
| API接口 | 1 | 1 | 见下文分模块说明 |

## 3. 域名与基础调用约定
### 3.1 官方文档里出现的域名
| 域名 | 出现次数 | 出现位置 | 集成建议 |
| --- | --- | --- | --- |
| api.yingdao.com | 30 | 鉴权、RPA 企业账号、工作队列、任务运行、JOB 运行、日志、机器人、应用、文件 | 默认公有云入口；私有化部署改用专有云域名 |
| api.winrobot360.com | 5 | 任务明细、任务列表、任务详情、最新执行记录 | 视为官方文档保留的兼容域名；生产接入以租户真实域名为准 |
### 3.2 统一认证与头部
- 先调用鉴权接口获取 `accessToken`。
- 后续接口统一在 Header 中携带 `Authorization: Bearer {accessToken}`。
- 除文件上传等特殊接口外，绝大多数接口使用 `Content-Type: application/json`。
- 官方说明明确指出 Token 最大有效期为 2 小时；如果 Token 未过期，重复请求鉴权接口会返回旧 Token。
### 3.3 通用返回格式
- 关键公共字段通常包括：`code`、`success`、`msg`、`requestId`、`data`。
- 调用方应始终记录 `requestId`，便于与影刀支持团队或平台侧日志对账。
- 官方状态码页把 `401/400/429/500` 列为最常见错误，企业接入时应显式区分“鉴权失败”“参数校验失败”“限流”“平台内部错误”。

## 4. 完整端点矩阵
| 模块 | 页面 | 方法 | 端点 | 官方页面 |
| --- | --- | --- | --- | --- |
| RPA企业账号 | 查询RPA企业账号列表 | GET | https://api.yingdao.com/oapi/rpa/user/v1/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710498885910380544 |
| RPA企业账号 | 创建RPA企业账号 | POST | https://api.yingdao.com/oapi/rpa/user/v1/create | https://www.yingdao.com/yddoc/rpa/zh-CN/710497757007953920 |
| RPA企业账号 | 修改RPA企业账号 | POST | https://api.yingdao.com/oapi/rpa/user/v1/modify | https://www.yingdao.com/yddoc/rpa/zh-CN/710496549620625408 |
| RPA企业账号 | 删除RPA企业账号 | POST | https://api.yingdao.com/oapi/rpa/user/v1/delete | https://www.yingdao.com/yddoc/rpa/zh-CN/710495670001700864 |
| RPA企业账号 | 重置账号密码 | POST | https://api.yingdao.com/oapi/useracl/v1/rest/pwd | https://www.yingdao.com/yddoc/rpa/zh-CN/710494844581036032 |
| 工作队列 | 重新排队 | PATCH | https://api.yingdao.com/oapi/tool/queue/v1/queueitems/{itemUuid}/reenqueue | https://www.yingdao.com/yddoc/rpa/zh-CN/717268756412026880 |
| 工作队列 | 修改队列项 | PATCH | https://api.yingdao.com/oapi/tool/queue/v1/queueitems/{{itemUuid}} | https://www.yingdao.com/yddoc/rpa/zh-CN/717268028778450944 |
| 工作队列 | 出列 | PATCH | https://api.yingdao.com/oapi/tool/queue/v1/queues/{{queueUuid}}/dequeue | https://www.yingdao.com/yddoc/rpa/zh-CN/717267384361996288 |
| 工作队列 | 新增队列项 | POST | https://api.yingdao.com/oapi/tool/queue/v1/queues/{{queueUuid}}/enqueue | https://www.yingdao.com/yddoc/rpa/zh-CN/710494036079095808 |
| 任务运行 | 启动任务API | POST | https://api.yingdao.com/oapi/dispatch/v2/task/start | https://www.yingdao.com/yddoc/rpa/zh-CN/710492920473436160 |
| 任务运行 | 查询任务运行结果API | POST | https://api.yingdao.com/oapi/dispatch/v2/task/query | https://www.yingdao.com/yddoc/rpa/zh-CN/710491717794512896 |
| 任务运行 | 停止任务运行API | POST | https://api.yingdao.com/oapi/dispatch/v2/task/stop | https://www.yingdao.com/yddoc/rpa/zh-CN/710490754371760128 |
| JOB运行 | 启动应用 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/start | https://www.yingdao.com/yddoc/rpa/zh-CN/710488569666060288 |
| JOB运行 | 查询应用运行结果API | POST | https://api.yingdao.com/oapi/dispatch/v2/job/query | https://www.yingdao.com/yddoc/rpa/zh-CN/710487379305533440 |
| JOB运行 | 停止应用运行API | POST | https://api.yingdao.com/oapi/dispatch/v2/job/stop | https://www.yingdao.com/yddoc/rpa/zh-CN/710486342769258496 |
| JOB运行 | 调度运行记录列表 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710485133474119680 |
| JOB运行 | 重试应用运行 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/retry | https://www.yingdao.com/yddoc/rpa/zh-CN/710483153807343616 |
| 运行日志 | 查询应用运行日志 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/log/search | https://www.yingdao.com/yddoc/rpa/zh-CN/710481967730900992 |
| 运行日志 | 通知查询应用运行日志 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/log/notify | https://www.yingdao.com/yddoc/rpa/zh-CN/710481123051515904 |
| 运行日志 | 轮询应用运行日志 | GET | https://api.yingdao.com/oapi/dispatch/v2/job/log/query | https://www.yingdao.com/yddoc/rpa/zh-CN/710479934544805888 |
| 机器人相关 | 查询机器人任务队列 | POST | https://api.yingdao.com/oapi/dispatch/v2/job/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710478762814193664 |
| 机器人相关 | 查询机器人分组列表 | POST | https://api.yingdao.com/oapi/dispatch/v2/client/group/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710477790566137856 |
| 机器人相关 | 查询机器人列表 | POST | https://api.yingdao.com/oapi/dispatch/v2/client/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710476864272334848 |
| 机器人相关 | 查询机器人信息 | POST | https://api.yingdao.com/oapi/dispatch/v2/client/query | https://www.yingdao.com/yddoc/rpa/zh-CN/710475766593617920 |
| 应用相关 | 查询应用列表API | POST | https://api.yingdao.com/oapi/app/open/query/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710474957390741504 |
| 应用相关 | 查询应用运行记录API | POST | https://api.yingdao.com/oapi/app/open/query/use/record/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710474186124374016 |
| 应用相关 | 查询应用主流程参数结构API | GET | https://api.yingdao.com/oapi/robot/v2/queryRobotParam | https://www.yingdao.com/yddoc/rpa/zh-CN/710473073333092352 |
| 应用相关 | 转移应用所有者API | POST | https://api.yingdao.com/oapi/app/open/translate/owner | https://www.yingdao.com/yddoc/rpa/zh-CN/710472302045138944 |
| 文件 | 文件上传 | POST | https://api.yingdao.com/oapi/dispatch/v2/file/upload | https://www.yingdao.com/yddoc/rpa/zh-CN/710470879923273728 |
| 任务 | 查询任务&机器人应用运行详情 | POST | https://api.winrobot360.com/oapi/dispatch/v2/task/process/detail | https://www.yingdao.com/yddoc/rpa/zh-CN/710469888978161664 |
| 任务 | 最新任务执行记录 | POST | https://api.winrobot360.com/oapi/dispatch/v2/task/newest/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710468955701456896 |
| 任务 | 单个任务执行记录列表 | POST | https://api.winrobot360.com/oapi/dispatch/v2/task/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710468004680773632 |
| 任务 | 查询任务详情 | POST | https://api.winrobot360.com/oapi/dispatch/v2/schedule/detail | https://www.yingdao.com/yddoc/rpa/zh-CN/710466731559485440 |
| 任务 | 查询任务列表 | POST | https://api.winrobot360.com/oapi/dispatch/v2/schedule/list | https://www.yingdao.com/yddoc/rpa/zh-CN/710465801475309568 |

## 5. RPA企业账号
负责企业调度账号的生命周期管理，适合对机器人执行账号进行集中创建、修改、密码重置和清理。

### 1. 查询RPA企业账号列表
- 页面路径：`开放API / API接口 / RPA企业账号 / 查询RPA企业账号列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710498885910380544>
- 调用方式：`GET` `https://api.yingdao.com/oapi/rpa/user/v1/list`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| phone | String | 否 | 完整的手机号 |
| accountKeyword | String | 否 | 账号关键词 |
| latestLoginTimeBegin | Long | 否 | 最后登录时间左边界，秒级时间戳 |
| latestLoginTimeEnd | Long | 否 | 最近登录时间右边界，秒级时间戳 |
| expiredTimeBegin | Long | 否 | 过期时间左边界，秒级时间戳 |
| expiredTimeEnd | Long | 否 | 过期时间右边界，秒级时间戳 |
| accountTypes | List<String> | 否 | 账号类型列表，基础账号-basic，高级账号-senior |
| page | int | 否 | 页码 |
| size | int | 否 | 一页默认20条，最大支持100 |

### 2. 创建RPA企业账号
- 页面路径：`开放API / API接口 / RPA企业账号 / 创建RPA企业账号`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710497757007953920>
- 调用方式：`POST` `https://api.yingdao.com/oapi/rpa/user/v1/create`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 说明 |
| --- | --- | --- |
| name | string | 员工姓名, 必填 |
| account | string | 账号, 必填 |
| phone | string | 手机号, 必填 |
| email | string | 邮箱, 可选 |
| accountType | string | 账号类型: basic 基础账号, senior 高级账号, 必填 |
| userRole | string | 用户角色: e_admin 管理员, e_user 员工, 必填 |
| password | string | 密码, 必填 |

### 3. 修改RPA企业账号
- 页面路径：`开放API / API接口 / RPA企业账号 / 修改RPA企业账号`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710496549620625408>
- 调用方式：`POST` `https://api.yingdao.com/oapi/rpa/user/v1/modify`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 说明 |
| --- | --- | --- |
| account | string | 账号, （确定需要修改的账号）, 必传 |
| name | string | 员工姓名, 传空(或者空串或者不传)表示不修改 |
| phone | string | 手机号, 传空(或者空串或者不传)表示不修改 |
| email | string | 邮箱, 传空(或者不传或者传空串)表示不修改 |
| userRole | string | 用户角色: e_admin 管理员, e_user 员工, 传空(或者空串或者不传)表示不修改 |

### 4. 删除RPA企业账号
- 页面路径：`开放API / API接口 / RPA企业账号 / 删除RPA企业账号`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710495670001700864>
- 调用方式：`POST` `https://api.yingdao.com/oapi/rpa/user/v1/delete`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 说明 |
| --- | --- | --- |
| account | string | 登录账号, （确定需要修改的账号）, 必传 |
| receiveAccount | string | 接收的登录账号（删除account账号时，将其开发的应用转移给receiveAccount账号）, 必传 |

### 5. 重置账号密码
- 页面路径：`开放API / API接口 / RPA企业账号 / 重置账号密码`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710494844581036032>
- 调用方式：`POST` `https://api.yingdao.com/oapi/useracl/v1/rest/pwd`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 说明 |
| --- | --- | --- |
| loginAccount | string | 账号, （确定需要修改的账号）, 必传 |
| oldPwd | string | 老密码，修改时需要和现有密码进行比对 |
| pwd | string | 新密码，不能为空 |

## 6. 工作队列
把业务对象拆成队列项进行流式消费，是企业级削峰、异步解耦和失败补偿的关键模块。
这一组不是“机器人调用接口”的附属功能，而是企业集成最重要的解耦层。业务系统应优先把对象压入队列，再让影刀按优先级与容量消费。

### 1. 重新排队
- 页面路径：`开放API / API接口 / 工作队列 / 重新排队`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/717268756412026880>
- 调用方式：`PATCH` `https://api.yingdao.com/oapi/tool/queue/v1/queueitems/{itemUuid}/reenqueue`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Accept | / |  |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| effectiveTime | Long | 是 | 生效时间，值为时间戳，单位：秒 |
| expireTime | Long | 否 | 过期时间，值为时间戳，单位：秒 |
| description | String | 否 | 描述，长度应在0~2000之间 |

### 2. 修改队列项
- 页面路径：`开放API / API接口 / 工作队列 / 修改队列项`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/717268028778450944>
- 调用方式：`PATCH` `https://api.yingdao.com/oapi/tool/queue/v1/queueitems/{{itemUuid}}`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Accept | / |  |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| status | String | 是 | 状态, processed、exception |
| description | String | 否 | 描述，长度应在0~2000之间 |

### 3. 出列
- 页面路径：`开放API / API接口 / 工作队列 / 出列`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/717267384361996288>
- 调用方式：`PATCH` `https://api.yingdao.com/oapi/tool/queue/v1/queues/{{queueUuid}}/dequeue`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Accept | / |  |

### 4. 新增队列项
- 页面路径：`开放API / API接口 / 工作队列 / 新增队列项`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710494036079095808>
- 调用方式：`POST` `https://api.yingdao.com/oapi/tool/queue/v1/queues/{{queueUuid}}/enqueue`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| name | String | 是 | 队列任务项名称，长度应在1~100之间 |
| priority | Integer | 是 | 优先级，枚举值 【0，100，200】<br>0-高，100-中，200-低 |
| expireTime | Long | 否 | 过期时间，值为时间戳，单位：秒 |
| effectiveTime | Long | 否 | 生效时间，值为时间戳，单位：秒 |
| bizInfo | String | 是 | 业务信息，长度应在1~1000之间 |
| description | String | 否 | 描述，长度应在0~2000之间 |
| source | String | 是 | 来源，使用 OpenAPI 即可 |

## 7. 任务运行
面向“任务/编排”模型，适合一个任务中包含多个应用与机器人关系、需要复杂调度编排的场景。
该组接口以 `task` 为核心标识，适合“调度中心中预先编排好的任务”。通常会关联 `scheduleUuid`、应用-机器人关系、参数透传以及更复杂的调度语义。

### 1. 启动任务API
- 页面路径：`开放API / API接口 / 任务运行 / 启动任务API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710492920473436160>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/task/start`

#### 集成要点
- 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明：该接口需要在控制台新建任务，编排好应用和机器人，适用于更复杂的调度场景，该接口也支持从外部传入应用运行参数，如果有多个应用，需要填写多个应用的运行参数，服务内部逻辑会根据robotUuid取出传入的应用运行参数，透传到客户端
- 影刀针对输入参数会有大小限制，一般建议所有输入参数加起来不超过8000，如遇到输入参数超过阈值，可有两种方案解决
- 方案一: 可以进行输入参数切割，如电商场景，1000个订单号传进来一次性调用，可以切割成100个订单号进行一次调用，将一次请求转换成10次
- 方案二: 可以把长文本转换成文件类型传递
- 步骤一:打开客户端，修改RPA流程，将字符串类型参数改成文件路径参数类型
- 步骤二 :保存并发版应用
- 步骤三:将文本参数转成文件上传到影刀文件服务器(文件上传)，返回文件key值
- 步骤三:api调用时，参数类型(type)修改成file类型，传入步骤三获取的文件key值
- 落地建议：无论是 `task/start` 还是 `job/start`，都应为每次业务请求生成唯一幂等标识，并把该标识与业务主键一同写入审计表。
- 落地建议：如果输入参数接近上限，优先使用“文件上传 -> file 类型参数”模式，不要把大文本直接塞进 JSON 体。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | accessToken变量需要替换成鉴权接口返回的accessToken |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| scheduleUuid | string | 任务uuid | 是 | 启动任务uuid，可在控制台-任务管理-右键获取 |
| idempotentUuid | string | 幂等uuid | 否 | 本次请求幂等uuid，建议使用uuid，避免网络重试多次触发任务执行, 影刀检测到两次请求的幂等id一样，会执行一次，并且第二次会返回上一次的taskUuid |
| scheduleRelaParams | array | 任务运行关联的应用参数 | 否 | 任务可能配置多个应用运行参数，是一个数组结构，需要指定robotUuid和对应的应用参数，如果没有指定，会取默认的应用运行参数 |
| ∟ robotUuid | string | 应用uuid | 否 | 带运行参数的应用uuid |
| ∟ runTimeout | number | 应用运行超时 | 否 | 可用于指定应用运行多长时间后自动停止， 常用来避免应用运行时间不可控或者卡死，影响排队任务运行，最小设置60 最大设置950400，单位秒，需要配合客户端5.10以及之上版本使用 |
| ∟ params | array | 应用运行参数 | 否 | 关联该应用的应用运行参数,最大不能超过8000长度 |
| ∟ name | string | 参数名称 | 否 | 参数名称 |
| ∟ value | string | 参数值 | 否 | 参数值 如果是文件类型可以使用文件上传接口文件上传接口先上传文件，将响应的fileKey作为参数值传递 |
| ∟ type | string | 参数类型 | 否 | 参数类型，参考：应用运行参数枚举值说明 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ taskUuid | string | 是 | 任务运行uuid |
| ∟ jobUuidList | array | 是 | 任务下每条应用的运行记录uuid集合 |
| ∟ idempotentFlag | boolean | 是 | 是否幂等创建标识，为true时表示重复创建，配合入参idempotentUuid使用 |

#### 请求示例
```json
// api调用任务
{
  "scheduleUuid": "79985266-f37a-4bb1-b456-b928914d3437",
  "idempotentUuid":"adss82cb-3333-111-1112-asdsad",
  "scheduleRelaParams": [
    {
      "robotUuid": "8ccc82cb-3945-4c7e-bb02-ab4ba4b183fd",
      "runTimeout":456,
      "params": [
        {
          "name": "str1",
          "value": "测试1",
          "type": "str"
        }
      ]
    }
  ]
}
```

#### 响应示例
```json
{
    "data": {
        "taskUuid": "fc38fbsa-8333-1111-83f8-3292aaaaaa",
        "jobUuidList": ["fd57564f-11f5-4035-a20f-b2838fcc0b05", "d64b1246-f0ef-436e-a948-01c325614e16"],
        "idempotentFlag": false
    },
    "code": 200,
    "success": true
}
```

### 2. 查询任务运行结果API
- 页面路径：`开放API / API接口 / 任务运行 / 查询任务运行结果API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710491717794512896>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/task/query`

#### 集成要点
- 需要先调用启动任务接口，获取taskUuid
- 说明：该接口是可以轮询任务运行结果，可获取任务下多个应用的运行结果数据，当任务运行结果处于终态时，需要停止轮询，任务运行状态参考 任务运行状态枚举说明
- 落地建议：把终态识别做成公共组件；一旦状态进入终态，立即停止轮询，改由回调/补偿任务收尾。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的accessToken |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| taskUuid | string | 任务运行uuid | 是 | 由启动任务接口返 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ taskUuid | string | 是 | 任务运行uuid |
| ∟ taskName | string | 是 | 任务名称 |
| ∟ status | string | 是 | 任务运行状态，该字段可以判断任务是否终态，终态时需要停止轮询该接口，参考：任务运行状态枚举说明 |
| ∟ statusName | string | 是 | 任务运行状态描述 |
| ∟ startTime | string | 否 | 任务运行开始时间，当任务被调度时不为空 |
| ∟ endTime | string | 否 | 任务运行结束时间，当任务结束运行时不为空 |
| ∟ jobDataList | array | 是 | 任务所关联的应用运行信息，多个应用有多条 |
| ∟ jobUuid | string | 是 | 应用运行uuid |
| ∟ status | string | 是 | 应用运行状态 |
| ∟ statusName | string | 是 | 应用运行状态描述 |
| ∟ remark | string | 否 | 备注信息，当运行异常，值不为空 |
| ∟ robotClientUuid | string | 否 | 机器人uuid，当应用已被调度之后，值不为空 |
| ∟ robotClientName | string | 否 | 机器人名称，当应用已被调度之后，值不为空 |
| ∟ startTime | string | 否 | 应用开始运行时间，当应用开始调度之后，值不为空 |
| ∟ endTime | string | 否 | 应用结束运行时间，当应用结束调度之后，值不为空 |
| ∟ robotUuid | string | 是 | 应用uuid |
| ∟ robotName | string | 是 | 应用名称 |
| ∟ screenshotUrl | string | 否 | job的截屏url |
| ∟ robotParams | object | 否 | 应用运行参数 |
| ∟ inputs | array | 否 | 输入参数 |
| ∟ name | string | 否 | 参数名称 |
| ∟ value | string | 否 | 参数值 |
| ∟ type | string | 否 | 参数类型，参考：任务运行状态枚举说明 |

#### 请求示例
```json
{
  "taskUuid":"4d8aae66-cec5-4043-85cc-70f4e0430111"
}
```

#### 响应示例
```json
{
    "data": {
        "taskUuid": "4d8aae66-cec5-4043-85cc-70f4e0430d4e",
        "taskName": "测试-api任务", 
        "status": "running",  
        "statusName": "运行中",
        "startTime": "2022-01-22 15:10:28",
        "endTime": "2022-01-22 15:10:46",
        "jobDataList": [
            {
                "jobUuid": "b934597c-f06d-4c52-9624-e62e7f7b9489",
                "status": "finish", 
                "statusName": "完成", 
                "remark": "", 
                "robotParams":  {
            				"name":"获取页数", 
            				"value":"10",
            				"type":"str" 
       					 }, 
                "robotClientUuid": "cfcc5904-2e82-4295-911c-0ce65c9099f2", 
                "robotClientName": "ceshi1@csqy1",
                "robotUuid": "3f3c9861-9300-4400-9c1f-f4e7f8bb4d08", 
                "robotName": "wait-10", 
                "startTime": "2022-01-22 15:10:28", 
                "endTime": "2022-01-22 15:10:46",
                "screenshotUrl": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/image/xxx.jpg"
            },
            {
                "jobUuid": "97421b0b-2f64-4adf-94b9-0bdfc73face6",
                "status": "created",
                "statusName": "已创建",
                "remark": "",
                "robotParams":  {
            				"name":"获取页数", 
            				"value":"10",
            				"type":"str" 
       					 }, 
                "robotClientUuid": "cfcc5904-2e82-4295-911c-0ce65c9099f2",
                "robotClientName": "ceshi1@csqy1",
                "robotUuid": "e8be5a0a-ec3a-4f3a-b4a2-b9319fe6fd0a",
                "robotName": "等待-10s",
               "startTime": "2022-01-22 15:10:28", 
                "endTime": "2022-01-22 15:10:46",
                "screenshotUrl": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/image/xxx.jpg"
            }
        ]
    },
    "code": 200,
    "success": true
}
```

### 3. 停止任务运行API
- 页面路径：`开放API / API接口 / 任务运行 / 停止任务运行API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710490754371760128>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/task/stop`

#### 集成要点
- 需要先调用启动任务接口，获取taskUuid
- 说明：任务运行状态处于终态，调用该接口无效果

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| taskUuid | string | 任务运行uuid | 是 | 无 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考： 状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |

#### 请求示例
```json
{
  "taskUuid": "45c882ed-e44f-4818-afc0-05172e7ff111"
}
```

#### 响应示例
```json
{
    "code": 200,
    "success": true
}
```

### 4. 任务运行回调
- 页面路径：`开放API / API接口 / 任务运行 / 任务运行回调`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710489613909069824>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 集成要点
- 1.使用管理员账号，在影刀控制台登录，在api配置界面配置回调接口；
- 2.确保接口是可以正常使用；
- 3.查看己方服务器环境，如果有防火墙，需要联系技术支持把影刀线上ip加入到白名单中；
- 4.需要先调用启动任务接口，获取jobUuid。
- 说明1：应用运行状态处于终态(正常结束，异常结束，已停止)，影刀服务会主动通过己方配置的回调接口回传job运行结果数据，推荐使用回调方式获取数据结果，保证数据及时获取到；
- 说明2：当己方回调接口返回2xx状态码时，影刀会任务对方正常接受并处理数据，不会进行定时补偿，当己方返回非2xx状态码时，影刀会每整点定时补偿一次，直到成功或者24次后，结束掉定时补偿，如果碰到任务状态超过24小时都没收到回调，建议调用查询任务运行结果。
- 落地建议：回调接口先快速返回 2xx，再异步处理业务逻辑；否则平台会进入小时级补偿重试。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| taskUuid | string | 是 | 应用运行uuid |
| dataType | string | 是 | 回调类型，调用方需要根据该字段，来解析不同回调类型的数据如:当dataType等于job时，表明是job/start接口触发回调，当dataType等于task时，表明是task/start接口触发回调，参考回调数据类型枚举值说明 |
| startTime | date | 是 | 第一个应用开始运行时间 |
| endTime | date | 是 | 最后一个应用结束运行时间 |
| msg | string | 是 | 任务运行备注 |
| status | string | 是 | 任务运行状态 |
| idempotentUuid | string | 是 | 本次请求幂等uuid，如果没传随机生成 |
| jobList | array |  | 任务下每个应用的运行列表 |
| ∟ jobUuid | string | 是 | 应用运行uuid |
| ∟ dataType | string | 是 | 回调类型，调用方需要根据该字段，来解析不同回调类型的数据如:当dataType等于job时，表明是job/start接口触发回调，当dataType等于task时，表明是task/start接口触发回调，参考回调数据类型枚举值说明 |
| ∟ status | string | 是 | 应用运行状态参考 应用运行状态枚举值说明 |
| ∟ screenshotUrl | string | 否 | 异常截屏，状态为error时才有 |
| ∟ msg | string | 否 | 应用运行信息，当应用运行异常时不为空 |
| ∟ startTime | string | 是 | 应用运行开始时间 |
| ∟ endTime | string | 是 | 应用运行结束时间 |
| ∟ robotClientUuid | string | 是 | 机器人uuid |
| ∟ robotClientName | string | 是 | 机器人名称 |
| ∟ robotName | string | 是 | 应用名称 |
| ∟ result | array | 否 | 应用运行输出参数 |
| ∟ name | string | 否 | 参数名称 |
| ∟ value | string | 否 | 参数值 |
| ∟ type | string | 否 | 参数类型，参考应用运行参数枚举值说明 |

#### 请求示例
```json
{
  "dataType": "task", //数据类型 job表示应用运行回调(通过api调用应用robotUuid的方式), task表示任务运行回调(通过api调用任务scheduleUuid的方式)
  "startTime": 1,//可为空 第一个应用开始运行时间
  "endTime": 1642837962000, //最后一个应用结束运行时间
  "jobList": [
    {
      "dataType": "job",
      "jobUuid": "6de893bb-8224-4f60-9bff-b8597b8ed8fc",
      "msg": "",
      "robotClientUuid": "cfcc5904-2e82-4295-911c-0ce65c9099f2",
      "robotClientName": "ceshi1@csqy1", //机器人名称
      "startTime":"2021-02-03 11:11:11", //该应用开始执行时间
      "endTime": "2021-03-03 12:12:12", //该应用结束执行时间
      "robotName": "导出淘宝订单", //应用名称
      "robotUuid": "xxxxx", //应用uuid
      "status": "finish",
      "idempotentUuid":"xxxx", //幂等id
      "screenshotUrl":"xxxx", //异常截屏
      "result": [ //有输出参数
                {
                    "name": "姓",
                    "value": "王",
                    "type": "str"  //参考应用运行参数枚举说明
                },
                {
                    "name": "名",
                    "value": "5",
                    "type": "str"  //参考应用运行参数枚举说明
                },
                {
                    "name": "上传文件",
                    "value": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/document/temp/request.txt",
                    "type": "file"  //参考应用运行参数枚举说明
                }
            ]
    }
  ],
  "msg": "运行结束", //任务运行备注
  "status": "finish", // 任务运行状态
  "taskUuid": "ea947f83-82fb-4afb-8412-4021255fd7cd"
}
```

## 8. JOB运行
面向“单应用 + 指定机器人/分组”的轻量调度模型，适合简单的一对一执行。
该组接口以 `job` 为核心标识，适合“我已经知道要在哪台机器人或机器人组上运行哪个应用”的直接调度模式。

### 1. 启动应用
- 页面路径：`开放API / API接口 / JOB运行 / 启动应用`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710488569666060288>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/start`

#### 集成要点
- 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 新创建的用户账号，必须先进过一次调度模式
- 说明：该接口是指定机器人/机器人分组以及单个应用去运行，适用于简单调度场景，如若涉及到复杂的多个机器人执行多个应用等，建议使用调度任务接口能力，另外获取应用运行信息可通过在控制台-api执行配置回调接口和查询应用运行详情接口获取
- 影刀针对输入参数会有大小限制，一般建议所有输入参数加起来不超过8000，如遇到输入参数超过阈值，可有两种方案解决
- 方案一: 可以进行输入参数切割，如电商场景，1000个订单号传进来一次性调用，可以切割成100个订单号进行一次调用，将一次请求转换成10次
- 方案二: 可以把长文本转换成文件类型传递
- 步骤一:打开客户端，修改RPA流程，将字符串类型参数改成文件路径参数类型
- 步骤二 :保存并发版应用
- 步骤三:将文本参数转成文件上传到影刀文件服务器(文件上传)，该接口会返回文件key值
- 步骤三:api调用时，参数类型(type)修改成file类型，传入步骤三获取的文件key值
- 落地建议：无论是 `task/start` 还是 `job/start`，都应为每次业务请求生成唯一幂等标识，并把该标识与业务主键一同写入审计表。
- 落地建议：如果输入参数接近上限，优先使用“文件上传 -> file 类型参数”模式，不要把大文本直接塞进 JSON 体。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的accessToken |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| accountName | string | 机器人账号名称 | 否 | accountName和robotClientGroupUuid互斥，二选一即可，accountName可在控制台-机器人管理列表复制名称 |
| robotClientGroupUuid | string | 机器人分组名称 | 否 | accountName和robotClientGroupUuid互斥，二选一即可，robotClientGroupUuid可在控制台-机器人分组列表复制UUID |
| robotUuid | string | 应用uuid | 是 | 登录控制台-应用管理-查看应用详情复制uuid |
| idempotentUuid | string | 幂等uuid | 否 | 为避免因为网络请求超时，导致重复启动任务，可指定本次请求的幂等uuid，影刀会判断当有多次相同幂等uuid请求时，只会成功过创建一次, 建议使用uuid，另外长度不可超过36位 |
| waitTimeout | string | 等待超时时间 即将作废 | 否 | 等待超时，可指定job排队时长 等待超时说明 |
| waitTimeoutSeconds | number | 等待超时时间单位秒 | 否 | 等待超时时间，单位秒，最小设置60(1分钟)，最大设置950400(11天), 默认600(10分钟) |
| runTimeout | number | 应用运行超时 | 否 | 可用于指定应用运行多长时间后自动停止， 常用来避免应用运行时间不可控或者卡死，影响排队任务运行，最小设置60 最大设置950400，单位秒，需要配合客户端5.10以及之上版本使用 |
| priority | string | 排队优先级 | 否 | 可通过该参数指定job在等待排队的优先级，参考等待排队优先级说明，默认是middle |
| executeScope | string | 执行范围，仅对机器人分组有作用 | 否 | any:机器人分组中随机一个机器人执行<br>all:机器人分组中全部机器人都执行 |
| params | object | 应用运行参数 | 否 | 共支持五种应用参数，最大支持params长度10000，应用运行参数说明，专有云6.0.0之前版本支持3000，之后版本支持8000 |
| ∟ name | string | 参数名称 | 否 | 参数名称 |
| ∟ value | string | 参数值 | 否 | 参数值 |
| ∟ type | string | 参数类型 | 否 | 参数类型，参考应用运行参数枚举值说明 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ jobUuid | string | 是 | 应用运行uuid，用于后续停止运行，查询运行状态入参 |
| ∟ idempotentFlag | boolean | 是 | 是否幂等创建标识，为true时表示重复请求，配合入参idempotentUuid使用 |

#### 请求示例
```json
{
  "accountName": "admin@fckj",
  "robotUuid": "73d9a119-7ec7-4226-b679-506afefae667", 
  "idempotentUuid":"69ba7c82-4087-42ca-b1ce-bd117bfea097",
  "waitTimeout":"10m",
  "executeScope":"any",
  "priority": "middle", 
  "params":[
    {
      "name":"获取页数", 
      "value":"10",
      "type":"str" 
    }
  ]
}
```

#### 响应示例
```json
{
    "data": {
        "jobUuid": "fc38f4f1-8444-475e-83f8-3292eeb1606b",
        "idempotentFlag": true
    },
    "code": 200,
    "success": true
}
```

### 2. 查询应用运行结果API
- 页面路径：`开放API / API接口 / JOB运行 / 查询应用运行结果API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710487379305533440>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/query`

#### 集成要点
- 需要先调用启动应用接口，获取jobUuid
- 说明：该接口是可以轮询获取job执行状态，一般可以配合回调接口使用，当回调接口收到job相关信息或者轮询到job状态是终态时，需要停止轮询，job运行状态参考应用运行状态枚举值说明，影刀建议的轮询频率是30s一次，
- 落地建议：把终态识别做成公共组件；一旦状态进入终态，立即停止轮询，改由回调/补偿任务收尾。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| jobUuid | string | 应用运行uuid | 是 | 通过启动job接口获 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ jobUuid | string | 是 | 应用运行uuid |
| ∟ status | string | 是 | 应用运行状态 |
| ∟ statusName | string | 是 | 应用运行状态描述 |
| ∟ remark | string | 否 | 备注信息，当运行异常，值不为空 |
| ∟ robotClientUuid | string | 否 | 机器人uuid，当应用已被调度之后，值不为空 |
| ∟ robotClientName | string | 否 | 机器人名称，当应用已被调度之后，值不为空 |
| ∟ startTime | string | 否 | 应用开始运行时间，当应用开始调度之后，值不为空 |
| ∟ endTime | string | 否 | 应用结束运行时间，当应用结束调度之后，值不为空 |
| ∟ robotUuid | string | 是 | 应用uuid |
| ∟ robotName | string | 是 | 应用名称 |
| ∟ screenshotUrl | string | 否 | job的截屏url |
| ∟ robotParams | object | 否 | 应用运行参数 |
| ∟ inputs | array | 否 | 输入参数 |
| ∟ item | object | 否 |  |
| ∟ name | string | 否 | 参数名称 |
| ∟ value | string | 否 | 参数值 |
| ∟ type | string | 否 | 参数类型，参考应用运行参数枚举值说明 |

#### 请求示例
```json
{
  "jobUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0"
}
```

#### 响应示例
```json
{
    "data": {
        "jobUuid": "42c2e0ce-499b-47aa-8642-3a1125b4759a",
        "status": "waiting",
        "statusName": "等待调度",
        "remark": "应用启动",
        "robotClientUuid": "00a7a1de-af0b-47ad-a3a8-a8fc2b009762",
        "robotClientName": "ceshi1@csqy1",
        "startTime":"2021-02-03 11:11:11", 
        "endTime": "2021-03-03 12:12:12",
        "robotUuid": "00a7a1de-af0b-47ad-a3a8-a8fc2b009761",
        "robotName": "打印日志应用",
        "screenshotUrl": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/image/xxx.jpg",
        "robotParams": {
            "inputs": [ 
                {
                    "name": "姓",
                    "value": "王",
                    "type": "str" 
                },
                {
                    "name": "名",
                    "value": "5",
                    "type": "str"  
                },
                {
                    "name": "上传文件",
                    "value": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/document/temp/request.txt",
                    "type": "file"  
                }
            ],
          "outputs":[ 
            {
                    "name": "姓",
                    "value": "王",
                    "type": "str"  
            }
          ]
        }
    },
    "code": 200,
    "success": true
}
```

### 3. 停止应用运行API
- 页面路径：`开放API / API接口 / JOB运行 / 停止应用运行API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710486342769258496>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/stop`

#### 集成要点
- 需要先调用启动应用应用接口，获取jobUuid
- 说明：应用运行状态处于终态，调用该接口无效果

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的accessToken |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| jobUuid | string | 应用运行uuid | 是 | 无 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |

#### 请求示例
```json
{
  "jobUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0"
}
```

#### 响应示例
```json
{
    "code": 200,
    "success": true
}
```

### 4. 调度运行记录列表
- 页面路径：`开放API / API接口 / JOB运行 / 调度运行记录列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710485133474119680>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/list`

#### 集成要点
- 说明： 查询调度运行记录列表

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| robotClientUuid | string | 机器人uuid | 否 | 机器人uuid，通过机器人列表接口获取 |
| scheduleUuid | string | 计划uuid | 否 | 计划uuid，通过任务列表接口获取 |
| statusList | array | 状态列表 | 否 | 参考 应用运行状态枚举值说明 |
| robotUuid | string | 应用uuid | 否 | 应用uuid，通过应用列表接口获取 |
| triggerTimeBegin | string | 触发时间-起 | 否 | 触发时间-起, 字符串, 格式是 “yyyy-MM-dd HH:mm:ss”, 如, 2025-11-10 10:00:00 |
| triggerTimeEnd | string | 触发时间-止 | 否 | 触发时间-止, 字符串, 格式是 “yyyy-MM-dd HH:mm:ss”, 如, 2025-11-10 10:00:00 |
| cursorId | long | 游标id | 否 | 游标id, 当第一页时，默认空 |
| cursorDirection | string | 翻页方向 | 是 | pre表示往上翻，next表示往下翻，默认为next |
| size | int | 每页数量 | 是 | 最小是1，最大是100，默认20 |
| queryApi | boolean | 只查询调度api触发的列表数据 | 否 | 默认false，该参数填写true，能实现控制台api执行记录列表 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| data | object | 是 |  |
| ∟code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| ∟success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| ∟msg | string | 是 | 状态码描述 |
| ∟hasData | boolean | 是 | 用于判断继续翻页时是否有数据，可用作翻页按钮置灰操作比如当往下翻页到20页时，第21页没有数据，则在20页时hasData为false，表示不能继续往下翻页，只能往上翻页 |
| ∟nextId | long | 是 | 往下翻页时，可作为 cursorId 使用，表示从这个id开始往下翻页 |
| ∟preId | long | 是 | 往上翻页时，可作为 cursorId 使用，表示从这个id开始往上翻页 |
| ∟cursorDirection | string | 是 | 当前的翻页方向 next表示当前往下翻页 pre表示当前往上翻页 |
| ∟dataList | array | 是 | 响应数据 |
| ∟ id | long | 是 | 游标id |
| ∟ jobUuid | string | 是 | 应用运行uuid |
| ∟ taskName | string | 是 | 任务名称 |
| ∟ status | string | 是 | 应用运行状态 |
| ∟ triggerTime | date | 是 | 触发时间，任务被触发的时间 |
| ∟ startTime | date | 否 | 应用开始运行时间，当应用开始调度之后，值不为空 |
| ∟ endTime | date | 否 | 应用结束运行时间，当应用结束运行时，值不为空 |
| ∟ robotUuid | string | 是 | 应用uuid |
| ∟ robotName | string | 是 | 应用名称 |
| ∟ remark | string | 否 | 应用运行异常备注 |
| ∟ robotClientUuid | string | 否 | 机器人uuid |
| ∟ robotClientName | string | 否 | 机器人名称 |

#### 请求示例
```json
{
  "robotClientUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0",
  "cursorDirection": "next", // 默认往下翻页
  "size": 20
}
```

#### 响应示例
```json
{
    "data": {
        "hasData": true,
        "nextId": 284065875470133276,
        "preId": 284065875470133295,
        "cursorDirection": "next",
        "dataList": [
            {
                "id": 284065875470133295,
                "jobUuid": "a54f25ef-9373-499a-afbb-79699f2c39e5",
                "status": "error",
                "taskName": "测试任务3",
                "robotUuid": "db5c419d-0ae7-4104-a313-45dc27ce3e49",
                "robotName": "应用A",
                "triggerTime": "2023-10-24 09:03:00",
                "robotClientUuid": "b21e8ffc-028c-40ae-a074-45a19f07cbda"
            },
            {
                "id": 284065875470133276,
                "jobUuid": "20db77a9-4126-412a-930c-0cc02c7b2d0c",
                "status": "error",
                "taskName": "测试3",
                "robotUuid": "799a2b1d-30ae-40ac-b011-f8a2beea5373",
                "robotName": "迁移测试",
                "triggerTime": "2023-10-24 09:00:00",
                "robotClientUuid": "b21e8ffc-028c-40ae-a074-45a19f07cbda"
            }
        ]
    },
    "code": 200,
    "success": true
}
```

### 5. 应用运行回调
- 页面路径：`开放API / API接口 / JOB运行 / 应用运行回调`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710484124829691904>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 集成要点
- 使用管理员账号，在影刀控制台登录，在api配置界面配置回调接口；
- 确保接口是可以正常使用 ；
- 查看己方服务器环境，如果有防火墙，需要联系技术支持把影刀线上ip加入到白名单中；
- 需要先调用启动应用接口，获取jobUuid。
- 说明1：应用运行状态处于终态(正常结束，异常结束，已停止)，影刀服务会主动通过己方配置的回调接口回传job运行结果数据，推荐使用回调方式获取数据结果，保证数据及时获取到。
- 说明2：当己方回调接口返回2xx状态码时，影刀会任务对方正常接受并处理数据，不会进行定时补偿，当己方返回非2xx状态码时，影刀会每整点定时补偿一次，直到成功或者24次后，结束掉定时补偿，如果碰到job状态超过24小时都没收到回调，建议调用查询应用运行结果。
- 落地建议：回调接口先快速返回 2xx，再异步处理业务逻辑；否则平台会进入小时级补偿重试。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| jobUuid | string | 是 | 应用运行uuid |
| dataType | string | 是 | 回调类型，调用方需要根据该字段，来解析不同回调类型的数据如:当dataType等于job时，表明是job/start接口触发回调，当dataType等于task时，表明是task/start接口触发回调，参考回调数据类型枚举值说明 |
| status | string | 是 | 应用运行状态参考 应用运行状态枚举值说明 |
| msg | string | 否 | 应用运行信息，当应用运行异常时不为空 |
| startTime | string | 是 | 应用运行开始时间 |
| endTime | string | 是 | 应用运行结束时间 |
| robotClientUuid | string | 是 | 机器人uuid |
| robotClientName | string | 是 | 机器人名称 |
| robotName | string | 是 | 应用名称 |
| idempotentUuid | string | 是 | 本次请求幂等uuid，如果没传随机生成 |
| result | array | 否 | 应用运行输出参数 |
| ∟ name | string | 否 | 参数名称 |
| ∟ value | string | 否 | 参数值 |
| ∟ type | string | 否 | 参数类型，参考应用运行参数枚举值说明 |

#### 请求示例
```json
{
	"jobUuid": "42c2e0ce-499b-47aa-8642-3a1125b4759a",
	"dataType": "job",
	"status": "finish",
	"msg": "执行结束",
	"robotClientUuid": "bfd28e42-e530-41eb-bf46-796a86ff7ec3",
	"robotClientName": "ceshi1@csqy1",
	"startTime": "2021-02-03 11:11:11",
	"endTime": "2021-03-03 12:12:12",
	"robotName": "导出淘宝订单",
	"robotUuid": "xxxxx",
  	"idempotentUuid":"xxxx",
	"result": [
		{
			"name": "姓",
			"value": "王",
			"type": "str"
		},
		{
			"name": "名",
			"value": "5",
			"type": "str"
		},
		{
			"name": "上传文件",
			"value": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/document/temp/request.txt",
			"type": "file"
		}
	]
}
```

### 6. 重试应用运行
- 页面路径：`开放API / API接口 / JOB运行 / 重试应用运行`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710483153807343616>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/retry`

#### 集成要点
- 需要先调用启动job接口，获取jobUuid
- 说明：应用运行状态非异常或已停止状态，重试无效果

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| jobUuid | string | 应用运行uuid | 是 | 无 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |

#### 请求示例
```json
{
  "jobUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0"
}
```

#### 响应示例
```json
{
    "code": 200,
    "success": true
}
```

## 9. 运行日志
提供日志搜索、通知式获取和轮询式获取三种手段，用于运行可观测性与故障排查。

### 1. 查询应用运行日志
- 页面路径：`开放API / API接口 / 运行日志 / 查询应用运行日志`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710481967730900992>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/log/search`

#### 集成要点
- ​ 需要先调用启动应用接口，或者通过其他的方式获取jobUuid
- 落地建议：把终态识别做成公共组件；一旦状态进入终态，立即停止轮询，改由回调/补偿任务收尾。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| jobUuid | string | 应用运行uuid | 是 | 通过启动应用接口获取 |
| page | int | 第几页 | 否 | 默认第一页 |
| size | int | 每页几条 | 否 | 默认20条 |
| queryFilter |  |  |  |  |
| ∟ beginTime | string | 结束时间 | 否 | 开始时间 |
| ∟ endTime | string | 开始时间 | 否 | 结束时间 |
| ∟ searchKey | string | 查询关键字 | 否 | 查询关键字 |
| ∟ sort | object | 排序字段 | 否 |  |
| ∟ sortKey | string | 排序key | 否 | 默认time，目前仅支持time |
| ∟ sortOrder | string | 排序顺序 | 否 | asc 升序 desc 降序 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，500表示失败 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 |  |
| ∟requestId |  |  |  |
| ∟ page |  |  |  |
| ∟ total | int | 是 | 总的数量 |
| ∟ page | int | 是 | 第几页 |
| ∟ size | int | 是 | 一页多少条 |
| ∟ logs | object | 否 | 无日志时为空 |
| ∟ time | string | 是 | 时间 参考 03/20/2024 15:35:23 |
| ∟ level | string | 是 | 日志等级 |
| ∟ text | string | 是 | 日志文本，不超过1K，超长会截取 |
| ∟ logId | long | 是 | 日志id |

#### 请求示例
```json
{
  "jobUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0",
  "page": 1,
  "size": 20,
  "queryFilter":{
    "beginTime":"2024-03-20 11:11:11",
    "endTime":"2024-03-20 11:11:12",
    "searchKey":"淘宝",
    "sort": {
      "sortKey": "time",
      "sortOrder": "desc"
    }
  }
}
```

#### 响应示例
```json
{
    "requestId":"xxxxx",
    "page": {
            "total": 18,
            "size": 10,
            "page": 1
        },
    "logs": [
            {
                "level": "信息",
                "logId": 1,
                "text": "开始执行...",
                "time": "03/20/2024 15:35:23"
            }
        ],    
      
}
```

### 2. 通知查询应用运行日志
- 页面路径：`开放API / API接口 / 运行日志 / 通知查询应用运行日志`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710481123051515904>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/log/notify`

#### 集成要点
- ​ 需要先调用启动应用接口，或者通过其他的方式获取jobUuid

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| jobUuid | string | 应用运行uuid | 是 | 通过启动应用接口获取 |
| page | int | 第几页 | 否 | 默认第一页 |
| size | int | 每页几条 | 否 | 默认20条 |
| queryFilter |  |  |  |  |
| ∟ beginTime | string | 结束时间 | 否 | 开始时间 |
| ∟ endTime | string | 开始时间 | 否 | 结束时间 |
| ∟ searchKey | string | 查询关键字 | 否 | 查询关键字 |
| ∟ sort | object | 排序字段 | 否 |  |
| ∟ sortKey | string | 排序key | 否 | 默认time，目前仅支持time |
| ∟ sortOrder | string | 排序顺序 | 否 | asc 升序 desc 降序 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，500表示查询失败，80204001表示(无法查询日志) |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | string | 是 | 本次请求的requestId |

#### 请求示例
```json
{
  "jobUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0",
  "page": 1,
  "size": 20,
  "queryFilter":{
    "beginTime":"2024-03-20 11:11:11",
    "endTime":"2024-03-20 11:11:12",
    "searchKey":"淘宝",
    "sort": {
      "sortKey": "time",
      "sortOrder": "desc"
    }
  }
}
```

#### 响应示例
```json
{
    "data": "5qwedqeasdc0zssadasdasdqwq",
    "code": 200,
    "success": true
}
```

### 3. 轮询应用运行日志
- 页面路径：`开放API / API接口 / 运行日志 / 轮询应用运行日志`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710479934544805888>
- 调用方式：`GET` `https://api.yingdao.com/oapi/dispatch/v2/job/log/query`

#### 集成要点
- ​ 需要先调用通知查询应用运行日志接口，获取requestld
- 说明：该接口可以使用requestId，轮询此次的日志，建议每隔100ms轮询一次，轮询超过100次
- code定义:
- 1.200：表示已经获取到日志
- 2.500: 表示错误，不用轮询
- 3.80204002：表明日志上传处理中，则需要继续轮询
- ps: 特殊情况，如果 通知查询应用运行日志 获取requestId后，超过60s再调用轮询应用运行日志接口，则日志会失效(云端日志保存60s)，则会提示该状态码
- 落地建议：把终态识别做成公共组件；一旦状态进入终态，立即停止轮询，改由回调/补偿任务收尾。

#### 请求头
|  |  |  |
| --- | --- | --- |
| 基本 |  | 说明 |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| requestId | string | 应用运行uuid | 是 | 通过启动应用接口获 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，500表示失败 , 80204002 表明处理中，需要继续轮询，建议轮询10s，如果还没有日志，则中断 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 本次请求的requestId |
| ∟ requestId |  |  |  |
| ∟ page |  |  |  |
| ∟ total | int | 是 | 总的数量 |
| ∟ page | int | 是 | 第几页 |
| ∟ size | int | 是 | 一页多少条 |
| ∟ logs | object | 否 | 无日志时为空 |
| ∟ time | string | 是 | 时间 参考 03/20/2024 15:35:23 |
| ∟ level | string | 是 | 日志等级 |
| ∟ text | string | 是 | 日志文本，不超过1K，超长会截取 |
| ∟ logId | long | 是 | 日志id |

#### 请求示例
```json
https://api.yingdao.com/oapi/dispatch/v2/job/log/query?requestId=xxx
```

## 10. 机器人相关
提供机器人、机器人分组、机器人队列的查询能力，是调度器做资源选择和容量决策的基础。

### 1. 查询机器人任务队列
- 页面路径：`开放API / API接口 / 机器人相关 / 查询机器人任务队列`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710478762814193664>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/job/list`

#### 集成要点
- ​ 需要到控制台，或者机器人列表接口获取机器人uuid
- 说明： 查询机器人当前的任务队列

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| robotClientUuid | string | 机器人uuid | 是 | 通过启动job接口获取 |
| cursorId | long | 游标id | 否 | 游标id, 当时第一页时，默认空 |
| cursorDirection | string | 游标方向 | 是 | pre表示往前翻，next表示往后翻 |
| size | int | 每页数量 | 是 | 最小是1，最大是100，默认20 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | array | 是 | 响应数据 |
| ∟ id | long | 是 | 瀑布流id |
| ∟ jobUuid | string | 是 | 应用运行uuid |
| ∟ taskName | string | 是 | 任务名称 |
| ∟ status | string | 是 | 应用运行状态 |
| ∟ triggerTime | date | 是 | 触发时间，任务被触发的事件 |
| ∟ startTime | date | 否 | 应用开始运行时间，当应用开始调度之后，值不为空 |
| ∟ robotUuid | string | 是 | 应用uuid |
| ∟ robotName | string | 是 | 应用名称 |

#### 请求示例
```json
{
  "robotClientUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0",
  "cursorDirection": "next",
  "size": 20
}
```

#### 响应示例
```json
{
    "data": [{
        "jobUuid": "42c2e0ce-499b-47aa-8642-3a1125b4759a",
        "status": "waiting",
        "statusName": "等待调度",
        "remark": "应用启动",
        "robotClientUuid": "00a7a1de-af0b-47ad-a3a8-a8fc2b009762",
        "robotClientName": "ceshi1@csqy1",
        "startTime":"2021-02-03 11:11:11", 
        "endTime": "2021-03-03 12:12:12",
        "robotUuid": "00a7a1de-af0b-47ad-a3a8-a8fc2b009761",
        "robotName": "打印日志应用",
        "robotParams": {
            "inputs": [ 
                {
                    "name": "姓",
                    "value": "王",
                    "type": "str" 
                },
                {
                    "name": "名",
                    "value": "5",
                    "type": "str"  
                },
                {
                    "name": "上传文件",
                    "value": "https://winrobot-pub-a-dev.oss-cn-hangzhou.aliyuncs.com/document/temp/request.txt",
                    "type": "file"  
                }
            ],
          "outputs":[ 
            {
                    "name": "姓",
                    "value": "王",
                    "type": "str"  
            }
          ]
        }
    }],
    "code": 200,
    "success": true
}
```

### 2. 查询机器人分组列表
- 页面路径：`开放API / API接口 / 机器人相关 / 查询机器人分组列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710477790566137856>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/client/group/list`

#### 集成要点
- ​ 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明： 该接口查询该租户下机器人分组列表

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| key | string | 关键字模糊搜索 效果等同like "xx%"，目前只对机器人分组名称有作用 | 否 | 关键字模糊搜索，支持右边模糊搜索，类似 like "xx%" |
| page | Integer | 分页参数，第一页 | 否 | 默认1，从第一页开始 |
| size | Integer | 分页参数，每页多少条 | 否 | 默认20,每页20 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | array | 是 | 响应数据 |
| ∟ robotClientGroupUuid | string | 是 | 机器人分组uuid |
| ∟ robotClientGroupName | string | 是 | 机器人分组名称 |
| page | objects | 是 | 分页信息 |
| ∟ total | int | 是 | 分页总数 |
| ∟ size | int | 是 | 每页数量 |
| ∟ page | int | 是 | 第几页 |
| ∟ pages | int | 是 | 分成多少页 |
| ∟ offset | int | 是 | 分页偏移量 |

#### 响应示例
```json
{
    "data": [
        {
            "uuid": "a3d67252-6795-4a69-99ef-bce60e67xxxd",
            "name": "double11",
        }
    ],
    "page": {
        "total": 5,
        "size": 20,
        "page": 1,
        "pages": 1,
        "offset": 0,
        "order": "desc"
    },
    "code": 200,
    "success": true
}
```

### 3. 查询机器人列表
- 页面路径：`开放API / API接口 / 机器人相关 / 查询机器人列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710476864272334848>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/client/list`

#### 集成要点
- ​ 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明： 该接口是可以指定参数筛选查询本企业下的所有机器人，返回字段包括状态，名称，以及机器人所在终端的信息，可用作构建机器人管理模块，也可用于筛选空闲的机器人派发任务

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| status | string | 机器人状态 | 否 | 机器人状态，参考机器人状态枚举值说明 |
| key | string | 关键字模糊搜索，目前只对机器人名称有作用 | 否 | 关键字模糊搜索，目前只对机器人名称有作用，等同于robotClientName |
| robotClientGroupUuid | string | 机器人分组uuid | 否 | 机器人分组uuid |
| page | Integer | 分页参数，第一页 | 是 | 第几页 |
| size | Integer | 分页参数，每页多少条 | 是 | 每页多少条 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | array | 是 | 响应数据 |
| ∟ robotClientUuid | string | 是 | 机器人uuid |
| ∟ robotClientName | string | 是 | 机器人名称，同accountName |
| ∟ status | string | 是 | 机器人状态，参考机器人状态枚举值说明 |
| ∟ description | string | 否 | 机器人备注描述 |
|  | object | 否 | 客户端终端信息 |
| ∟ windowsAccount | string | 否 | 客户端系统账号 |
| ∟ clientIp | string | 否 | 客户端系统ip |
| ∟ machineName | string | 否 | 客户端系统host名称 |

#### 请求示例
```json
{
  "page":1,
  "size": 10
}
```

#### 响应示例
```json
{
  "data": [{
    "robotClientUuid": "xxx",
    "robotClientName": "admin@ydsc",
    "status": "idle",
    "description": "rpa001",
    "windowsUserName": "by",
    "clientIp": "127.0.0.1",
    "machineName": "RPA-PC"
  }],
  "page": {
    "total": 100,
    "size": 10,
    "page": 1,
    "pages": 10
  },
  "code": 0,
  "success": true,
  "msg": "success"
}
```

### 4. 查询机器人信息
- 页面路径：`开放API / API接口 / 机器人相关 / 查询机器人信息`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710475766593617920>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/client/query`

#### 集成要点
- ​ 需要到控制台-机器人管理，复制机器人账号或者机器人uuid，机器人uuid目前需要F12抓包从client/list接口获取uuid
- 说明： 该接口是可以获取机器人信息，支持机器人名称或者机器人uuid查询，只需要填其中一个，两个都填的情况，请确认名称和uuid对的上，建议用机器人名称查询，因为机器人移出后，重新切换调度模式，机器人uuid会生成新的。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| accountName | string | 机器人账号名称 | 否 | accountName和robotClientUuid互斥，二选一即可，推荐使用机器人账号 |
| robotClientUuid | string | 机器人uuid | 否 | accountName和robotClientGroupUuid互斥，二选一即可，机器人uuid目前需要F12抓包从client/list接口获取uuid |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ robotClientUuid | string | 是 | 机器人uuid |
| ∟ robotClientName | string | 是 | 机器人名称，同accountName |
| ∟ status | string | 是 | 机器人状态，参考机器人状态枚举值说明 |
| ∟ description | string | 否 | 机器人备注描述 |
| ∟ remark | string | 否 | 运行备注 |
| ∟ clientIp | string | 是 | 客户端ip |

#### 请求示例
```json
{
  "accountName": "boyi@csqy"
}
```

#### 响应示例
```json
{
    "data": {
        "robotClientUuid": "0d6a835a-2e08-414a-af73-1e43f9d9c8ff",
        "robotClientName": "ceshi1@csqy1",
        "status": "idle",
        "description": "ceshi1",
        "clientIp": "172.16.28.156", 
      	"remark": "运行成功"
        
    },
    "code": 200,
    "success": true
}
```

## 11. 应用相关
提供应用目录、应用运行记录、主流程参数结构和所有权转移能力，适合资产治理与变更管理。

### 1. 查询应用列表API
- 页面路径：`开放API / API接口 / 应用相关 / 查询应用列表API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710474957390741504>
- 调用方式：`POST` `https://api.yingdao.com/oapi/app/open/query/list`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| appId | String | 否 | 应用ID |
| size | String | 否 | 一页大小，默认30，最大100 |
| page | String | 否 | 页码 默认1 |
| ownerUserSearchKey | String | 否 | 用户搜索关键字，仅支持账号精确匹配 |
| appName | String | 否 | 应用名称模糊匹配 |

### 2. 查询应用运行记录API
- 页面路径：`开放API / API接口 / 应用相关 / 查询应用运行记录API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710474186124374016>
- 调用方式：`POST` `https://api.yingdao.com/oapi/app/open/query/use/record/list`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| appId | String | 否 | 应用ID,与时间筛选必传其中之一 |
| size | String | 否 | 一页大小，默认30，最大100 |
| minId | int | 是 | 游标分页字段，每次传上一页最大id作为起始id，不传则minId默认0 |
| beginDate | String | 否 | 开始时间,与应用筛选必传其中之一 |
| endDate | String | 否 | 结束时间,与应用筛选必传其中之一 |

### 3. 查询应用主流程参数结构API
- 页面路径：`开放API / API接口 / 应用相关 / 查询应用主流程参数结构API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710473073333092352>
- 调用方式：`GET` `https://api.yingdao.com/oapi/robot/v2/queryRobotParam`

#### 集成要点
- 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明：该接口只能查询已经发版过的应用

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | accessToken变量需要替换成鉴权接口返回的access Token |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | array | 是 | 响应数据 |
| ∟ inputParams | array | 否 | 入参 |
| ∟ name | string | 是 | 参数名称 |
| ∟ direction | string | 是 | 入参出参 |
| ∟ type | string | 是 | 参数类型，str,float,file等五种类型 |
| ∟ value | string | 是 | 参数值 |
| ∟ description | string | 是 | 参数描述 |
| ∟ kind | string | 是 | kind是客户端的一个定义，目前不需要。字符串他对应的类型是Text |
| ∟ outputParams | array |  | 出参同上 |
| ∟ 同上 |  |  |  |

#### 响应示例
```json
{
    "data": {
        "inputParams": [
            {
                "name": "input_str_variable",
                "direction": "In",
                "type": "str",
                "value": "",
                "description": "",
                "kind": "Text"
            },
            {
                "name": "input_float_variable",
                "direction": "In",
                "type": "float",
                "value": "0.0",
                "description": "",
                "kind": "Expression"
            },
            {
                "name": "input_bool_variable",
                "direction": "In",
                "type": "bool",
                "value": "False",
                "description": "",
                "kind": "Expression"
            },
            {
                "name": "input_file_variable",
                "direction": "In",
                "type": "file",
                "value": "",
                "description": "",
                "kind": "Text"
            }
        ],
        "outputParams": [
            {
                "name": "input_int_variable",
                "direction": "Out",
                "type": "int",
                "value": "0",
                "description": "",
                "kind": "Expression"
            }
        ]
    },
    "code": 200,
    "success": true,
    "requestId": "7484425d-2525-4b58-aacf-50f205a603fd"
}
```

### 4. 转移应用所有者API
- 页面路径：`开放API / API接口 / 应用相关 / 转移应用所有者API`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710472302045138944>
- 调用方式：`POST` `https://api.yingdao.com/oapi/app/open/translate/owner`

#### 集成要点
- 使用鉴权接口获取accessToken。

#### 请求头
| 基本 | 参数值 | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| appId | String | 是 | 应用ID |
| receiveUserAccount | String | 是 | 接收人账号，需要精确匹配 |

## 12. 文件
提供文件上传入口，可把长文本或大参数先转成文件，再通过 file 类型参数传入应用。

### 1. 文件上传
- 页面路径：`开放API / API接口 / 文件 / 文件上传`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710470879923273728>
- 调用方式：`POST` `https://api.yingdao.com/oapi/dispatch/v2/file/upload`

#### 集成要点
- ​ 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明： 该接口用于调度api 启动任务或者启动应用场景，当流程中有文件类型输入参数时，先调用该接口完成文件上传，该接口会返回一个文件key，将文件key作为输入参数传递即可，影刀调度程序会根据文件key构建成机器人可识别下载的文件url。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken} 变量需要替换成鉴权接口返回的access Token |
| Content-Type | multipart/form-data |  |

#### 关键请求字段
| 名称 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| file | file | 是 | 目标文件的二进制文件流，具体用法请参照上面的示例代码 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟fileKey | string | 是 | 文件fileKey， 用于启动应用和启动任务 文件类型输入参数 |

#### 响应示例
```json
{
    "data": {
        "fileKey": "aedbdaad-0c9c-4c05-9082-be42f0ba03a2"
    },
    "code": 200,
    "success": true
}
```

## 13. 任务
提供调度记录、任务详情、最新执行记录和单任务执行明细，适合后台对账、审计和运维看板。

### 1. 查询任务&机器人应用运行详情
- 页面路径：`开放API / API接口 / 任务 / 查询任务&机器人应用运行详情`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710469888978161664>
- 调用方式：`POST` `https://api.winrobot360.com/oapi/dispatch/v2/task/process/detail`

#### 集成要点
- ​ 1.调用该接口前请获取taskUuid以及robotClientUuid，作为参数，可通过查询单个任务详情接口以及最新执行记录接口获取taskUuid和robotClientUuid
- 说明： 该接口可以获取该条任务运行记录下该客户端所有应用运行记录，等同于中控平台执行记录-点击具体某个客户端查看应用运行详情
- 兼容性备注：官方页面显示的是 `api.winrobot360.com`。建议把该域名视为文档事实来源，而不是生产默认值；生产配置应通过环境变量或配置中心覆盖。
- 落地建议：把终态识别做成公共组件；一旦状态进入终态，立即停止轮询，改由回调/补偿任务收尾。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| taskUuid | string | 任务运行uuid | 是 | 通过启动任务接口获取 |
| robotClientUuid | string | 机器人uuid | 是 | 机器人uuid |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ jobList | array | 是 | 应用运行记录 |
| ∟ jobUuid | string | 是 | 应用运行记录uuid |
| ∟ taskUuid | string | 是 | 任务运行记录uuid |
| ∟ status | string | 是 | 应用运行状态，参考应用运行状态枚举值说明 |
| ∟ createTime | string | 是 | 创建时间，一般等同触发时间 |
| ∟ updateTime | string | 是 | 更新时间 |
| ∟ dispatchCount | number | 是 | 调度次数 |
| ∟ startTime | string | 否 | 开始运行时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ endTime | string | 否 | 结束运行时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ existsParam | boolean | 是 | 是否存在输入/输出参数 |
| ∟ priority | string | 是 | 优先级 参考优先级枚举值说明 |
| ∟ remark | string | 是 | 应用运行备注，当应用运行报错后，该字段可视为错误备注 |
| ∟ robotClientUuid | string | 是 | 机器人uuid |
| ∟ robotName | string | 是 | 应用名称 |
| ∟ robotUuid | string | 是 | 应用uuid |
| ∟ screenshotUrl | string | 否 | 错误截屏url，当应用运行某一次运行异常后，值不为空 |
| ∟ sourceType | string | 是 | 执行来源类型，参考执行来源类型枚举值说明 |
| ∟ sourceUuid | string | 是 | 执行来源uuid，一般等同于scheduleUuid |

#### 请求示例
```json
{
  "taskUuid": "45c882ed-e44f-4818-afc0-05172e7ffbe0",
  "robotClientUuid": "b2c85558-2ecb-421c-99db-fa2bd56de123"
}
```

### 2. 最新任务执行记录
- 页面路径：`开放API / API接口 / 任务 / 最新任务执行记录`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710468955701456896>
- 调用方式：`POST` `https://api.winrobot360.com/oapi/dispatch/v2/task/newest/list`

#### 集成要点
- ​ 说明：该接口用户获取每条任务最新执行记录
- 说明： 该接口是可以指定参数筛选查询本企业下的所有机器人，返回字段包括状态，名称，以及机器人所在终端的信息，可用作构建机器人管理模块，也可用于筛选空闲的机器人派发任务
- 兼容性备注：官方页面显示的是 `api.winrobot360.com`。建议把该域名视为文档事实来源，而不是生产默认值；生产配置应通过环境变量或配置中心覆盖。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| statusList | array | 任务运行状态集合 | 否 | 参考任务运行状态说明 |
|  | string | 子项 | 否 |  |
| startTime | string | 开始时间 | 否 | 开始时间，以触发时间进行查询 |
| endTime | string | 结束时间 | 否 | 结束时间，以触发时间进行查询 |
| page | number | 页码 | 否 | 分页参数，第几页 默认1 |
| size | number | 页数 | 否 | 分页参数一页多少条，默认20 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ cursorDirection | string | 是 | 游标方向，next表明下一页，pre表示上一页 |
| ∟ hasData | boolean | 是 | 是否还有下一页数据 |
| ∟ nextId | number | 是 | 下一页id |
| ∟ preId | number | 是 | 上一页id |
| ∟ dataList | array | 是 | 任务所关联的应用运行信息，多个应用有多条 |
| ∟ createTime | string | 是 | 创建时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ updateTime | string | 是 | 更新时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ executeScope | string | 是 | 机器人执行策略 参考机器人执行策略枚举说明 |
| ∟ clientScope | string |  |  |
| ∟ taskName | string | 是 | 任务运行名称，等同于taskName |
| ∟ id | numer | 是 | 任务运行id |
| ∟ sourceUuid | string | 是 | 来源uuid，一般是scheduleUuid |
| ∟ sourceType | string | 是 | 来源类型，参考执行来源枚举说明 |
| ∟ status | string | 是 | 任务运行状态，该字段可以判断任务是否终态，终态时需要停止轮询该接口，参考任务运行状态枚举说明 |
| ∟ taskUuid | string | 是 | 任务运行uuid 等同于sceneInstUuid |
| ∟ userUuid | string | 是 | 触发用户uuid |
| ∟ userName | string | 否 | 触发用户名称 |
| ∟ runTimes | number | 是 | 任务运行次数 |
| ∟ taskClients | array | 是 | 等同sceneInstClients |
| ∟ clientIp | string | 否 | 机器人客户端ip |
| ∟ robotClientStatus | string | 是 | 机器人状态 参考机器人状态枚举说明 |
| ∟ currentRobotUuid | string | 否 | 当前运行引用uuid |
| ∟ currentRobotName | string | 否 | 当前运行应用名称 |
| ∟ description | string | 否 | 机器人备注名称 |
| ∟ robotClientName | string | 否 | 机器人名称 |
| ∟ robotClientUuid | string | 否 | 机器人uuid |

#### 请求示例
```json
{
  "startTime":"2022-05-15 17:50:00",
  "endTime":"2022-05-16 17:50:00",
  "statusList":["finish","running"],
  "page":1,
  "size": 20
}
```

### 3. 单个任务执行记录列表
- 页面路径：`开放API / API接口 / 任务 / 单个任务执行记录列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710468004680773632>
- 调用方式：`POST` `https://api.winrobot360.com/oapi/dispatch/v2/task/list`

#### 集成要点
- ​ 1.通过任务列表接口获取scheduleUuid作为sourceUuid传入
- 说明： 该接口获取单个任务执行记录，可用作点击具体某个任务时，展示任务下所有的执行记录(以瀑布流展示)，不支持跳页
- 兼容性备注：官方页面显示的是 `api.winrobot360.com`。建议把该域名视为文档事实来源，而不是生产默认值；生产配置应通过环境变量或配置中心覆盖。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |  |
| --- | --- | --- | --- | --- | --- |
| sourceUuid | string | 来源uuid | 是 | 任务uuid |  |
| statusList | array | 任务运行状态集合 | 否 | 参考任务运行状态说明 |  |
|  | string | 子项 | 否 |  |  |
| startTime | string | 开始时间 | 否 | 开始时间，以触发时间进行查询 |  |
| endTime | string | 结束时间 | 否 | 结束时间，以触发时间进行查询 |  |
| cursorId | number | 分页游标id | 否 | 第一页时不用传，点击下一页时需要传，该值取上一页最后一条记录id即可,点击上一页时，该值取上一次请求记录的第一条记录id即可 |  |
| cursorDirection | string | 分页方向 | 是 | pre:点击上一页，next:点击下一页，第一页时默认next |  |
| size | number | 每页多少条 | 是 | number | 每页多少 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ cursorDirection | string | 是 | 游标方向，next表明下一页，pre表示上一页 |
| ∟ hasData | boolean | 是 | 是否还有下一页数据 |
| ∟ nextId | number | 是 | 下一页id |
| ∟ preId | number | 是 | 上一页id |
| ∟ dataList | array | 是 | 任务所关联的应用运行信息，多个应用有多条 |
| ∟ createTime | string | 是 | 创建时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ updateTime | string | 是 | 更新时间 格式yyyy-mm-dd hh:MM:dd |
| ∟ executeScope | string | 是 | 机器人执行策略 参考机器人执行策略枚举说明 |
| ∟ clientScope | string |  |  |
| ∟ taskName | string | 是 | 任务运行名称，等同于taskName |
| ∟ id | numer | 是 | 任务运行id |
| ∟ sourceUuid | string | 是 | 来源uuid，一般是scheduleUuid |
| ∟ sourceType | string | 是 | 来源类型，参考执行来源枚举说明 |
| ∟ status | string | 是 | 任务运行状态，该字段可以判断任务是否终态，终态时需要停止轮询该接口，参考任务运行状态枚举说明 |
| ∟ taskUuid | string | 是 | 任务运行uuid 等同于sceneInstUuid |
| ∟ userUuid | string | 是 | 触发用户uuid |
| ∟ userName | string | 否 | 触发用户名称 |
| ∟ runTimes | number | 是 | 任务运行次数 |
| ∟ taskClients | array | 是 | 等同sceneInstClients |
| ∟ clientIp | string | 否 | 机器人客户端ip |
| ∟ robotClientStatus | string | 是 | 机器人状态 参考机器人状态枚举说明 |
| ∟ currentRobotUuid | string | 否 | 当前运行引用uuid |
| ∟ currentRobotName | string | 否 | 当前运行应用名称 |
| ∟ description | string | 否 | 机器人备注名称 |
| ∟ robotClientName | string | 否 | 机器人名称 |
| ∟ robotClientUuid | string | 否 | 机器人uuid |

#### 请求示例
```json
{
  "sourceUuid":"4d8aae66-cec5-4043-85cc-70f4e0430111",
  "startTime":"2022-05-15 17:50:00",
  "endTime":"2022-05-16 17:50:00",
  "statusList":["finish","running"],
  "cursorId":123,
  "cursorDirection": "next",
  "size":10
}
```

### 4. 查询任务详情
- 页面路径：`开放API / API接口 / 任务 / 查询任务详情`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710466731559485440>
- 调用方式：`POST` `https://api.winrobot360.com/oapi/dispatch/v2/schedule/detail`

#### 集成要点
- ​ 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明： 该接口查询单个任务详情，适用于用户自己建设任务管理功能
- 兼容性备注：官方页面显示的是 `api.winrobot360.com`。建议把该域名视为文档事实来源，而不是生产默认值；生产配置应通过环境变量或配置中心覆盖。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| scheduleUuid | string | 任务uuid | 是 | 从任务列表接口中获取 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ scheduleUuid | string | 是 | 任务uuid |
| ∟ scheduleName | string | 是 | 任务名称 |
| ∟ scheduleType | string | 是 | 任务类型，参考任务类型枚举值说明 |
| ∟ createTime | string | 是 | 创建时间 yyyy-mm-dd hh:MM:ss |
| ∟ updateTime | string | 是 | 更新时间 yyyy-mm-dd hh:MM:ss |
| ∟ clientScope | string | 是 | 机器人选择范围 参考机器人选择范围 |
| ∟ executeScope | string | 是 | 机器人执行策略 机器人执行策略枚举说明 |
| ∟ creatorName | string | 是 | 创建人账号 |
| ∟ creatorUuid | string | 是 | 创建人uuid |
| ∟ modifierName | string | 是 | 修改人账号 |
| ∟ modifierUuid | string | 是 | 修改人uuid |
| ∟ enabled | boolean | 是 | 是否启用任务 |
| ∟ enabledWaitTimeout | boolean | 是 | 是否开启等待超时设置 |
| ∟ errorProcess | string | 是 | 错误执行策略 异常执行策略枚举说明 |
| ∟ newestTaskUuid | string | 否 | 最新一次任务运行uuid |
| ∟ runTimes | number | 是 | 运行时间 |
| ∟ priority | number | 是 | 运行次数 |
| ∟ robotClientList | array | 是 | 机器人相关 |
| ∟ uuid | string** ** | 是 | 机器人uuid |
| ∟ robotClientName | string | 否 | 机器人名称，机器人被删除时为空 |
| ∟ robotList | array | 是 | 应用相关 |
| ∟ enableRunTimeout | boolean | 是 | 是否开启应用运行超时设置 |
| ∟ icon | string | 否 | 图标 |
| ∟ robotName | string | 否 | 应用名称，如果应用被删除，为空 |
| ∟ robotUuid | string | 否 | 应用uuid，如果应用被删除，为空 |
| ∟ supportParam | boolean | 是 | 是否支持应用参数 |
| ∟ settings | array | 否 | 当 supportParam = true时， 应用主流程参数不为空 |
| ∟ inputs | array | 否 | 应用主流程输入参数 |
| ∟ description | string | 否 | 参数描述 |
| ∟ direction | string | 否 | 参数方向 Out为出参，In为入参 |
| ∟ name | string | 否 | 参数名称 |
| ∟ type | string | 否 | 参数类型，参考应用类型参数类型枚举值说明 |
| ∟ value | string | 否 | 参数值 |
| ∟ outputs | array | 否 | 应用主流程输出参数 |
| ∟ description | string | 否 | 参数描述 |
| ∟ direction | string | 否 | 参数方向 Out为出参，In为入参 |
| ∟ name | string | 否 | 参数名称 |
| ∟ type | string | 否 | 参数类型，参考应用类型参数类型枚举值说明 |
| ∟ value | string | 否 | 参数值 |
| ∟ userGrantList | array | 是 | 任务用户授权相关 |
| ∟ userUuid | string | 是 | 用户uuid |
| ∟ accountName | string | 是 | 用户账号名称 |
| ∟ waitTimeoutSettings | object | 是 | 超时设置 |
| ∟ waitTimeoutDay | number | 否 | 等待超时 以天为单位 |
| ∟ waitTimeoutHour | number | 否 | 等待超时 以小时为单位 |
| ∟ waitTimeoutMin | number | 否 | 等待超时 以分钟为单位 |
| ∟ cronInterface | object | 是 | 定时器 |
| ∟ cronExpress | string | 否 | cron表达式 |
| ∟ dayOfWeeks | number | 否 | 周天 |
| ∟ hour | number | 否 | 小时 |
| ∟ minimumIntervalSeconds | number | 否 | 最小秒 |
| ∟ minute | numner | 否 | 分钟 |
| ∟ month | numner | 否 | 月 |
| ∟ nextTime | string | 否 | 下一次触发时间 yyyy-mm-dd hh:MM:ss |
| ∟ time | string | 否 | 时分秒 |
| ∟ type | string | 否 | 定时器类型 参考定时器类型枚举说明 |

#### 请求示例
```json
{
  "scheduleUuid":"xxx"
}
```

### 5. 查询任务列表
- 页面路径：`开放API / API接口 / 任务 / 查询任务列表`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710465801475309568>
- 调用方式：`POST` `https://api.winrobot360.com/oapi/dispatch/v2/schedule/list`

#### 集成要点
- ​ 需要使用鉴权接口获取accessToken后，填写到对应的hearder中
- 说明： 该接口查询租户下所有任务列表，适用场景用于建立自己的任务管理功能
- 兼容性备注：官方页面显示的是 `api.winrobot360.com`。建议把该域名视为文档事实来源，而不是生产默认值；生产配置应通过环境变量或配置中心覆盖。

#### 请求头
| 基本 |  | 说明 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | {accessToken}变量需要替换成鉴权接口返回的access Token |
| Content-Type | application/json |  |

#### 关键请求字段
| 名称 | 类型 | 说明 | 是否必填 | 描述 |
| --- | --- | --- | --- | --- |
| key | string | 搜索关键字 | 否 | 目前作用在任务名称模糊搜索 |
| enabled | boolean | 是否启用 | 否 | 是否启用任务 |
| scheduleType | string | 任务类型 | 否 | 参考任务类型枚举值说明 |
| page | number | 分页之第几页 | 否 | 默认值1，从第一页开始 |
| size | number | 分页之每页多少条 | 否 | 默认值20，一页20条，该值最高上限500 |

#### 关键响应字段
| 名称 | 类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| code | int | 是 | 状态码 200表示成功，非200表示失败 参考：状态码说明 |
| success | boolean | 是 | 调用是否成功，可以根据该字段判断接口调用是否成功 |
| msg | string | 是 | 状态码描述 |
| data | object | 是 | 响应数据 |
| ∟ scheduleUuid | string | 是 | 任务uuid |
| ∟ scheduleName | string | 是 | 任务名称 |
| ∟ scheduleType | string | 是 | 任务类型，参考任务类型枚举值说明 |
| ∟ createTime | string | 是 | 创建时间 yyyy-mm-dd hh:MM:ss |
| ∟ updateTime | string | 是 | 更新时间 yyyy-mm-dd hh:MM:ss |
| ∟ cronInterface | object | 是 | 定时器 |
| ∟ cronExpress | string | 否 | cron表达式 |
| ∟ dayOfWeeks | number | 否 | 周天 |
| ∟ hour | number | 否 | 小时 |
| ∟ minimumIntervalSeconds | number | 否 | 最小秒 |
| ∟ minute | numner | 否 | 分钟 |
| ∟ month | numner | 否 | 月 |
| ∟ nextTime | string | 否 | 下一次触发时间 yyyy-mm-dd hh:MM:ss |
| ∟ time | string | 否 | 时分秒 |
| ∟ type | string | 否 | 定时器类型 参考定时器类型枚举说明 |

#### 请求示例
```json
{
  "key":"测试",
  "enabled":true,
  "type":"period",
  "page":1,
  "size":10,
  "orderBy":"createTime"
}
```

## 14. 通用说明
涵盖限流、枚举、响应格式、参数类型和 FAQ，是所有企业集成前必须补齐的运行约束层。
本组页面决定了企业方案的可运营性：限流、响应格式、枚举与 FAQ 都在这里。建议在开发、测试、生产环境分别固化成平台规范。

### 1. 限流说明
- 页面路径：`开放API / 通用说明 / 限流说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/912893828744491008>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 架构解读
- 这张限流表不应该只被开发同学看见，而应被纳入 API Gateway、任务编排器和 SRE 配额系统。
- 企业做批量调用时，应按端点分桶限速，而不是只做“全局每秒请求数”控制。
- 日志相关接口的限额更低（例如 `job/log/search`、`job/log/notify`、`job/log/query`），因此日志回放和审计任务要尽量离峰执行。

### 2. 常见问题说明
- 页面路径：`开放API / 通用说明 / 常见问题说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710463081711124480>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 集成要点
- 调用job/start或者task/start不成功
- 未使用专有云地址进行请求
- 使用专有云地址进行请求
- key和secret不对，可能在使用公有云的key和secret
- 根据提示调整key和secret
- 用户可能直接copy了接口注释
- postMan不会识别注释，直接去掉注释即可
- 目前接口存在两个维度，一个是task/xxx,一个是job/xxx, job/xxx提供一些简单1:1指定机器人和应用运行方式，不提供编排能力，task是需要在控制台新建任务，通过任务uuid指定启动，提供更丰富的能力
- 接口信息传入错误，比如job/stop. 却使用taskUuid进行停止
- 使用正确的参数，jobUuid和taskUuid分别由job/start,task/start接口返回

#### 架构解读
- 官方 FAQ 本质上暴露了最容易踩的 4 类坑：域名选错、task/job 混用、回调链路不通、账号与机器人选择策略理解偏差。
- 这些问题不应留到线上排障阶段解决，而应在“接入前验证清单”里一次性检查。

### 3. 应用主流程参数说明
- 页面路径：`开放API / 通用说明 / 应用主流程参数说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710462821173268480>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

### 4. 状态码说明
- 页面路径：`开放API / 通用说明 / 状态码说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710462530950475776>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

### 5. 响应格式说明
- 页面路径：`开放API / 通用说明 / 响应格式说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710462272255164416>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

### 6. 枚举值说明
- 页面路径：`开放API / 通用说明 / 枚举值说明`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710460954567454720>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 集成要点
- 终态可以作为是否停止轮询的唯一标识

#### 架构解读
- 所有轮询器、状态机和监控看板都应直接复用这里的枚举值，不要在业务代码里二次翻译后再判断。
- 终态集合至少要覆盖：任务 `finish/stopped/error`，应用 `finish/stopped/error/skipped/cancel`。

## 15. 参考案例下载
官方给出的 Postman、Java、Python、验签材料下载页，适合作为接入样板仓。

### 1. 参考案例下载
- 页面路径：`开放API / 参考案例下载`
- 官方页面：<https://www.yingdao.com/yddoc/rpa/zh-CN/710460379288813568>
- 调用方式：该页面是说明类页面，通常描述回调载荷、枚举、限流、FAQ 或案例下载。

#### 集成要点
- 调度开放api汇总.json （右键另存为）
- xybot-api-sdk.rar （右键另存为）
- apiDispatch.py （右键另存为）
- SignDemoNew.java（右键另存为）
- 说明:
- accessKeyId：影刀控制台生成的accessKeyId，登录后选择API执行->API配置
- bodyMd5：请求体加密的字符串，可由回调接口回传回去
- timestamp：精确到秒的时间戳即可，由回调接口回传回去

## 17. 企业级接入建议
### 17.1 先做“能力地图”，再做代码对接
- 先确定业务对象是“单应用直接运行”还是“复杂编排任务”，从而决定优先对接 `job/*` 还是 `task/*`。
- 先确定是否要把长参数落文件、是否需要工作队列、是否必须回调，再开始设计调用链。
- 先确定机器人池模型（指定机器人、指定分组、随机空闲、全部执行），再讨论 AI 调度和成本优化。
### 17.2 推荐的最小生产闭环
1. 通过鉴权接口拿 Token。
2. 通过应用/任务接口校验目标资源是否存在。
3. 对大参数先走文件上传。
4. 调用 `job/start` 或 `task/start`。
5. 将 `jobUuid/taskUuid/idempotentUuid/requestId` 写入业务表。
6. 同时启用“回调接收 + 轮询兜底”。
7. 根据终态停止轮询，并通过日志接口抓取关键日志和截图 URL。
8. 把运行结果、成本、异常、SLA 写回上游系统或 BI。

## 18. 官方来源索引
以下页面均来自影刀帮助中心“开放 API”目录，本次文档以这些页面为事实基线：
- `开放API / API接口 / 鉴权`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710499792859115520>
- `开放API / API接口 / RPA企业账号 / 查询RPA企业账号列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710498885910380544>
- `开放API / API接口 / RPA企业账号 / 创建RPA企业账号`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710497757007953920>
- `开放API / API接口 / RPA企业账号 / 修改RPA企业账号`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710496549620625408>
- `开放API / API接口 / RPA企业账号 / 删除RPA企业账号`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710495670001700864>
- `开放API / API接口 / RPA企业账号 / 重置账号密码`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710494844581036032>
- `开放API / API接口 / 工作队列 / 重新排队`: <https://www.yingdao.com/yddoc/rpa/zh-CN/717268756412026880>
- `开放API / API接口 / 工作队列 / 修改队列项`: <https://www.yingdao.com/yddoc/rpa/zh-CN/717268028778450944>
- `开放API / API接口 / 工作队列 / 出列`: <https://www.yingdao.com/yddoc/rpa/zh-CN/717267384361996288>
- `开放API / API接口 / 工作队列 / 新增队列项`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710494036079095808>
- `开放API / API接口 / 任务运行 / 启动任务API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710492920473436160>
- `开放API / API接口 / 任务运行 / 查询任务运行结果API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710491717794512896>
- `开放API / API接口 / 任务运行 / 停止任务运行API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710490754371760128>
- `开放API / API接口 / 任务运行 / 任务运行回调`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710489613909069824>
- `开放API / API接口 / JOB运行 / 启动应用`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710488569666060288>
- `开放API / API接口 / JOB运行 / 查询应用运行结果API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710487379305533440>
- `开放API / API接口 / JOB运行 / 停止应用运行API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710486342769258496>
- `开放API / API接口 / JOB运行 / 调度运行记录列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710485133474119680>
- `开放API / API接口 / JOB运行 / 应用运行回调`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710484124829691904>
- `开放API / API接口 / JOB运行 / 重试应用运行`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710483153807343616>
- `开放API / API接口 / 运行日志 / 查询应用运行日志`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710481967730900992>
- `开放API / API接口 / 运行日志 / 通知查询应用运行日志`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710481123051515904>
- `开放API / API接口 / 运行日志 / 轮询应用运行日志`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710479934544805888>
- `开放API / API接口 / 机器人相关 / 查询机器人任务队列`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710478762814193664>
- `开放API / API接口 / 机器人相关 / 查询机器人分组列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710477790566137856>
- `开放API / API接口 / 机器人相关 / 查询机器人列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710476864272334848>
- `开放API / API接口 / 机器人相关 / 查询机器人信息`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710475766593617920>
- `开放API / API接口 / 应用相关 / 查询应用列表API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710474957390741504>
- `开放API / API接口 / 应用相关 / 查询应用运行记录API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710474186124374016>
- `开放API / API接口 / 应用相关 / 查询应用主流程参数结构API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710473073333092352>
- `开放API / API接口 / 应用相关 / 转移应用所有者API`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710472302045138944>
- `开放API / API接口 / 文件 / 文件上传`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710470879923273728>
- `开放API / API接口 / 任务 / 查询任务&机器人应用运行详情`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710469888978161664>
- `开放API / API接口 / 任务 / 最新任务执行记录`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710468955701456896>
- `开放API / API接口 / 任务 / 单个任务执行记录列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710468004680773632>
- `开放API / API接口 / 任务 / 查询任务详情`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710466731559485440>
- `开放API / API接口 / 任务 / 查询任务列表`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710465801475309568>
- `开放API / 通用说明 / 限流说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/912893828744491008>
- `开放API / 通用说明 / 常见问题说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710463081711124480>
- `开放API / 通用说明 / 应用主流程参数说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710462821173268480>
- `开放API / 通用说明 / 状态码说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710462530950475776>
- `开放API / 通用说明 / 响应格式说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710462272255164416>
- `开放API / 通用说明 / 枚举值说明`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710460954567454720>
- `开放API / 参考案例下载`: <https://www.yingdao.com/yddoc/rpa/zh-CN/710460379288813568>
