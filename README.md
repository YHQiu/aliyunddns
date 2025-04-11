Aliyun DDNS Updater
License: MIT
自动检测公网IP变化并更新阿里云DNS解析记录的轻量级工具

功能特性
🌍 多AK配置支持（不同AccessKey管理不同域名）

⏱️ 智能更新策略（15秒检测IP，5分钟限频更新）

📝 YAML配置文件管理

📊 完善的日志系统

🖥️ 支持作为系统服务运行

快速开始
环境要求
Python 3.6+

阿里云账号（需开通DNS解析服务）

安装依赖
```bash
pip install -r requirements.txt
````
配置文件
复制模板文件：
```commandline
cp config.example.yaml aliyun_ddns_config.yaml
```

编辑配置：

```yaml
ak_configs:
  - access_key_id: "您的AK"
    access_key_secret: "您的SK"
    domains:
      - domain: "example.com"
        rr: "www"
        type: "A"

ip_check_interval: 15
dns_update_min_interval: 300
```

运行方式
直接运行
```commandline
python app.py
```

作为系统服务（Linux）
```text
创建服务文件 /etc/systemd/system/aliyun-ddns.service：
```

```ini
[Unit]
Description=Aliyun DDNS Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /path/to/app.py
WorkingDirectory=/path/to/project
Restart=always
User=root
```

[Install]
WantedBy=multi-user.target
启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable aliyun-ddns
sudo systemctl start aliyun-ddns
```

开源协议
本项目采用 MIT License 开源协议

```text
MIT License

Copyright (c) [2025] [qhy/vvpixel.inc 深圳市生动像素科技有限公司]

Permission is hereby granted...
```

```
项目结构
.
├── app.py                # 主程序
├── aliyun_ddns_config.yaml  # 配置文件
├── config.example.yaml   # 配置模板
├── requirements.txt      # 依赖列表
├── LICENSE               # 开源协议
└── README.md            # 说明文档
配套文件说明
requirements.txt
```

```text
pyyaml>=5.4.1
aliyun-python-sdk-core>=2.13.36
aliyun-python-sdk-alidns>=2.0.8
requests>=2.26.0
config.example.yaml
```

```yaml
# 阿里云DDNS配置模板

ak_configs:
  - access_key_id: "your_ak"
    access_key_secret: "your_sk"
    domains:
      - domain: "example.com"
        rr: "www"
        type: "A"
```

# 检测间隔(秒)
ip_check_interval: 15
dns_update_min_interval: 300

# 日志配置
```text
log_file: "/var/log/aliyun_ddns.log"
```
LICENSE

```text
MIT License

Copyright (c) 2025 vvpixel.inc

Permission is hereby granted...
```
