"""
日志生成工具 - 用于收集系统信息并生成综合报告
"""
import os
import sys
import platform
import logging
import json
import datetime
import psutil
from app.core.config import settings
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class LogGenerator:
    """日志生成器类 - 用于收集系统信息并生成综合报告"""
    
    def __init__(self, output_dir="logs/reports"):
        """初始化日志生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.report_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = os.path.join(output_dir, f"system_report_{self.report_time}.log")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    
    def collect_system_info(self):
        """收集系统信息"""
        system_info = {
            "系统": platform.system(),
            "系统版本": platform.version(),
            "系统架构": platform.architecture(),
            "Python版本": sys.version,
            "处理器": platform.processor(),
            "主机名": platform.node(),
            "CPU核心数": psutil.cpu_count(),
            "总内存(GB)": round(psutil.virtual_memory().total / (1024**3), 2),
            "可用内存(GB)": round(psutil.virtual_memory().available / (1024**3), 2),
            "磁盘使用情况": self._get_disk_usage(),
            "运行时间(小时)": round(psutil.boot_time() / 3600, 2),
            "当前工作目录": os.getcwd()
        }
        return system_info
    
    def collect_app_settings(self):
        """收集应用配置信息"""
        # 过滤掉敏感信息如密码和令牌
        safe_settings = {}
        for key, value in vars(settings).items():
            if not key.startswith("__") and not any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]):
                safe_settings[key] = value
        return safe_settings
    
    def collect_error_logs(self, days=7):
        """收集最近的错误日志
        
        Args:
            days: 收集最近几天的日志
        """
        error_logs = []
        logs_dir = os.path.join(os.getcwd(), "logs")
        
        if not os.path.exists(logs_dir):
            return ["日志目录不存在"]
        
        # 计算最早日期
        earliest_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # 查找错误日志文件
        for log_file in os.listdir(logs_dir):
            if log_file.startswith("error_") and log_file.endswith(".log"):
                try:
                    # 从文件名提取日期
                    date_str = log_file[6:-4]  # 提取error_YYYYMMDD.log中的YYYYMMDD部分
                    file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
                    
                    # 检查日期是否在范围内
                    if file_date >= earliest_date:
                        log_path = os.path.join(logs_dir, log_file)
                        with open(log_path, "r", encoding="utf-8") as f:
                            # 读取最后100行错误日志
                            lines = f.readlines()[-100:]
                            error_logs.extend([f"{log_file}: {line.strip()}" for line in lines])
                except Exception as e:
                    logger.error(f"读取错误日志文件失败: {e}")
        
        return error_logs
    
    def collect_adb_devices(self):
        """收集连接的ADB设备信息"""
        try:
            result = subprocess.run(
                ["adb", "devices"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.stdout.strip().split("\n")
        except Exception as e:
            logger.error(f"获取ADB设备信息失败: {e}")
            return [f"获取ADB设备信息失败: {str(e)}"]
    
    def collect_task_stats(self):
        """收集任务统计信息（调用数据库）"""
        try:
            from app.db.session import SessionLocal
            from app.models.task import Task, TaskStatus
            from sqlalchemy import func
            
            db = SessionLocal()
            try:
                # 获取各状态任务数量
                task_counts = db.query(
                    Task.status, 
                    func.count(Task.id).label('count')
                ).group_by(Task.status).all()
                
                # 获取今日任务数量
                today = datetime.datetime.now().strftime("%Y%m%d")
                today_count = db.query(func.count(Task.id)).filter(
                    func.substr(func.cast(Task.time, "text"), 1, 8) == today
                ).scalar()
                
                # 获取最近执行失败的任务
                recent_failures = db.query(Task).filter(
                    Task.status.in_([TaskStatus.ERR, TaskStatus.UPERR])
                ).order_by(Task.updatetime.desc()).limit(5).all()
                
                failure_info = [{
                    "id": task.id,
                    "device": task.device_name,
                    "status": task.status,
                    "updatetime": task.updatetime
                } for task in recent_failures]
                
                return {
                    "状态分布": {status: count for status, count in task_counts},
                    "今日任务数": today_count,
                    "最近失败任务": failure_info
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取任务统计信息失败: {e}")
            return {"error": str(e)}
    
    def _get_disk_usage(self):
        """获取磁盘使用情况"""
        usage = {}
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                # 在Windows上跳过CD-ROM和未挂载的驱动器
                continue
            usage[part.mountpoint] = {
                "总空间(GB)": round(psutil.disk_usage(part.mountpoint).total / (1024**3), 2),
                "已用空间(GB)": round(psutil.disk_usage(part.mountpoint).used / (1024**3), 2),
                "可用空间(GB)": round(psutil.disk_usage(part.mountpoint).free / (1024**3), 2),
                "使用率": f"{psutil.disk_usage(part.mountpoint).percent}%"
            }
        return usage
    
    def generate_report(self):
        """生成综合报告"""
        try:
            # 收集各种信息
            system_info = self.collect_system_info()
            app_settings = self.collect_app_settings()
            error_logs = self.collect_error_logs()
            adb_devices = self.collect_adb_devices()
            task_stats = self.collect_task_stats()
            
            # 创建报告
            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write(f"===== 系统报告 - 生成时间: {self.report_time} =====\n\n")
                
                # 写入系统信息
                f.write("===== 系统信息 =====\n")
                for key, value in system_info.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # 写入应用配置
                f.write("===== 应用配置 =====\n")
                for key, value in app_settings.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # 写入ADB设备信息
                f.write("===== ADB设备 =====\n")
                for line in adb_devices:
                    f.write(f"{line}\n")
                f.write("\n")
                
                # 写入任务统计
                f.write("===== 任务统计 =====\n")
                f.write(json.dumps(task_stats, indent=2, ensure_ascii=False))
                f.write("\n\n")
                
                # 写入错误日志
                f.write("===== 最近错误日志 =====\n")
                for log_line in error_logs:
                    f.write(f"{log_line}\n")
            
            logger.info(f"系统报告已生成: {self.report_path}")
            return self.report_path
        
        except Exception as e:
            logger.error(f"生成系统报告失败: {e}")
            return None
    
    def archive_logs(self, days_to_keep=30):
        """将旧日志归档
        
        Args:
            days_to_keep: 保留最近几天的日志，其他归档
        """
        try:
            logs_dir = os.path.join(os.getcwd(), "logs")
            archive_dir = os.path.join(logs_dir, "archive")
            
            if not os.path.exists(logs_dir):
                return False
            
            # 创建归档目录
            os.makedirs(archive_dir, exist_ok=True)
            
            # 计算保留的日期
            keep_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            # 遍历日志文件
            for log_file in os.listdir(logs_dir):
                if not os.path.isfile(os.path.join(logs_dir, log_file)):
                    continue
                    
                if log_file.endswith(".log"):
                    try:
                        # 尝试从文件名提取日期
                        date_part = None
                        if log_file.startswith("app_") or log_file.startswith("error_"):
                            date_part = log_file.split("_")[1].split(".")[0]  # 提取YYYYMMDD部分
                        
                        if date_part and len(date_part) == 8:  # 确保是8位日期格式
                            file_date = datetime.datetime.strptime(date_part, "%Y%m%d")
                            
                            # 如果日志文件超过保留期，则归档
                            if file_date < keep_date:
                                src_path = os.path.join(logs_dir, log_file)
                                dst_path = os.path.join(archive_dir, log_file)
                                shutil.move(src_path, dst_path)
                                logger.info(f"已归档旧日志: {log_file}")
                    except Exception as e:
                        logger.error(f"归档日志文件失败: {log_file}, 错误: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"归档日志失败: {e}")
            return False


def generate_system_report():
    """生成系统报告的快捷函数"""
    generator = LogGenerator()
    report_path = generator.generate_report()
    if report_path:
        logger.info(f"系统报告已生成在: {report_path}")
        return report_path
    else:
        logger.error("生成系统报告失败")
        return None


if __name__ == "__main__":
    # 设置日志
    from app.core.logger import setup_logger
    setup_logger()
    
    # 生成报告
    report_path = generate_system_report()
    print(f"报告已生成: {report_path}")
    
    # 归档旧日志
    log_gen = LogGenerator()
    log_gen.archive_logs() 