#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author  : qiuhongyu@vvpixel.inc
# @File    : app.py
# @Software: PyCharm
# @Desc    :
import os

import requests
import json
import time
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109 import DescribeDomainRecordsRequest, UpdateDomainRecordRequest

# 默认配置文件路径
CONFIG_FILE = Path(__file__).parent / 'aliyun_ddns_config.yaml'
os.makedirs("/var/log/aliyun_ddns", exist_ok=True)
os.makedirs("/tmp/aliyun_ddns/", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/aliyun_ddns/aliyun_ddns.log'),
        logging.StreamHandler()
    ]
)

class DDNSService:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.last_ip = None
        self.ip_changed = False
        self.clients = {}

        # 初始化阿里云客户端
        for ak_config in self.config['ak_configs']:
            client = AcsClient(
                ak_config['access_key_id'],
                ak_config['access_key_secret'],
                ak_config.get('region', 'cn-hangzhou')
            )
            self.clients[ak_config['access_key_id']] = {
                'client': client,
                'domains': ak_config['domains']
            }

    def load_config(self, config_file):
        """加载YAML配置文件"""
        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                config = yaml.safe_load(f)

                # 设置默认值
                config.setdefault('ip_check_interval', 15)
                config.setdefault('dns_update_min_interval', 300)
                config.setdefault('ip_cache_file', '/tmp/aliyun_ddns/aliyun_ddns_ip_cache.txt')
                config.setdefault('last_update_file', '/tmp/aliyun_ddns/aliyun_ddns_last_update.txt')
                config.setdefault('log_file', '/var/log/aliyun_ddns.log')
                config.setdefault('ip_check_services', [
                    'https://api.ipify.org?format=json',
                    'http://ip-api.com/json',
                    'https://ipinfo.io/json'
                ])

                return config
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    def get_public_ip(self):
        """获取当前公网IP地址"""
        for service in self.config['ip_check_services']:
            try:
                response = requests.get(service, timeout=10)
                data = response.json()

                if 'ipify.org' in service:
                    return data['ip']
                elif 'ip-api.com' in service:
                    return data['query']
                elif 'ipinfo.io' in service:
                    return data['ip']
            except Exception as e:
                logging.warning(f"从 {service} 获取IP失败: {str(e)}")
                continue

        raise Exception("所有IP查询服务都不可用")

    def get_cached_ip(self):
        """获取缓存的IP地址"""
        try:
            if not os.path.isfile(self.config['ip_cache_file']):
                return None
            with open(self.config['ip_cache_file'], 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def cache_ip(self, ip):
        """缓存当前IP地址"""
        with open(self.config['ip_cache_file'], 'w') as f:
            f.write(ip)

    def get_last_update_time(self):
        """获取最后更新时间"""
        try:
            with open(self.config['last_update_file'], 'r') as f:
                return datetime.fromisoformat(f.read().strip())
        except (FileNotFoundError, ValueError):
            return datetime.min

    def update_last_update_time(self):
        """更新最后修改时间"""
        with open(self.config['last_update_file'], 'w') as f:
            f.write(datetime.now().isoformat())

    def get_record_id(self, client, domain, rr, record_type):
        """获取域名记录的RecordId"""
        request = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
        request.set_DomainName(domain)
        request.set_accept_format('json')

        response = client.do_action_with_exception(request)
        records = json.loads(response)['DomainRecords']['Record']

        logging.info(f"获取到域名记录信息： {records}")

        for record in records:
            if record['RR'] == rr and record['Type'] == record_type:
                return record['RecordId'], record['Value']

        return None, None

    def update_dns_record(self, client, domain, rr, record_type, record_id, current_ip):
        """更新DNS记录"""
        request = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
        request.set_RecordId(record_id)
        request.set_RR(rr)
        request.set_Type(record_type)
        request.set_Value(current_ip)
        request.set_accept_format('json')

        response = client.do_action_with_exception(request)
        result = json.loads(response)

        if result.get('RecordId'):
            logging.info(f"成功更新记录: {rr}.{domain} -> {current_ip}")
            return True
        else:
            logging.error(f"更新记录失败: {rr}.{domain}")
            return False

    def can_update_dns(self):
        """检查是否可以进行DNS更新"""
        last_update = self.get_last_update_time()
        logging.info(f"上次更新DNS时间是：{last_update}")
        return datetime.now() - last_update >= timedelta(seconds=self.config['dns_update_min_interval'])

    def run(self):
        """运行DDNS服务"""

        logging.info("阿里云DDNS服务启动")

        while True:
            try:
                self.last_ip = self.get_cached_ip()
                current_ip = self.get_public_ip()

                logging.info(f"获取到本机公网IP地址是：{current_ip}")

                if self.last_ip != current_ip:
                    logging.info(f"检测到IP变化: {self.last_ip} -> {current_ip}")
                    self.ip_changed = True
                    # 如果IP变化且满足时间间隔条件，则更新DNS
                    if self.ip_changed and self.can_update_dns():
                        logging.info("开始更新DNS记录...")

                        self.last_ip = current_ip
                        self.cache_ip(current_ip)

                        for ak_id, config in self.clients.items():
                            client = config['client']
                            domains = config['domains']

                            for domain_info in domains:
                                domain = domain_info['domain']
                                rr = domain_info['rr']
                                record_type = domain_info['type']

                                record_id, record_value = self.get_record_id(client, domain, rr, record_type)
                                if not record_id:
                                    logging.warning(f"AK {ak_id[:4]}...: 未找到记录 {rr}.{domain}, 跳过更新")
                                    continue

                                if record_value != current_ip:
                                    self.update_dns_record(client, domain, rr, record_type, record_id, current_ip)
                                    self.update_last_update_time()
                                    logging.info("更新完成，更新结果是：{}")
                                else:
                                    logging.info(f"AK {ak_id[:4]}...: 记录 {rr}.{domain} 已经是当前IP, 无需更新")
                        self.ip_changed = False
                    else:
                        logging.info("IP 变化，但是不满足阿里云更新频率，所有需要等待下一次更新.")

            except Exception as e:
                logging.error(f"发生错误: {str(e)}", exc_info=True)

            time.sleep(self.config['ip_check_interval'])

if __name__ == '__main__':
    try:
        service = DDNSService(CONFIG_FILE)
        service.run()
    except KeyboardInterrupt:
        logging.info("服务被用户中断")
    except Exception as e:
        logging.error(f"服务异常终止: {str(e)}", exc_info=True)