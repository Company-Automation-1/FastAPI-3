```bash
app/
├── core/                 # 核心配置
│   ├── config.py        # 配置管理
│   └── database.py      # 数据库连接
├── models/              # 数据模型
│   └── device.py        # 设备模型
├── services/            # 业务逻辑
│   └── device.py        # 设备服务
└── api/                 # API路由
    └── v1/             # API版本
        └── device.py    # 设备API
```

# 表现层（API 层）
 - app/api/v1/device.py
 - 处理 HTTP 请求和响应
 - 参数验证
 - 路由管理
# 业务逻辑层（Service 层）
 - app/services/device.py
 - 实现业务逻辑
 - 协调数据访问
# 数据访问层（Model 层）
 - app/models/device.py
 - 数据结构定义
 - 数据库交互