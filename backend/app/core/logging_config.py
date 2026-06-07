"""
FastAPI 企业级日志配置
支持请求日志、按日期轮转、结构化输出
"""
import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON 格式化器，用于结构化日志输出"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration
        if hasattr(record, 'ip'):
            log_data['client_ip'] = record.ip
        if hasattr(record, 'user_agent'):
            log_data['user_agent'] = record.user_agent
        if hasattr(record, 'params'):
            log_data['params'] = record.params
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """人类可读的格式化器"""
    
    def format(self, record):
        # 基本信息
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        base_msg = f"[{timestamp}] [{record.levelname}] {record.getMessage()}"
        
        # 添加请求详情
        details = []
        if hasattr(record, 'method') and hasattr(record, 'path'):
            details.append(f"{record.method} {record.path}")
        if hasattr(record, 'status_code'):
            details.append(f"Status: {record.status_code}")
        if hasattr(record, 'duration'):
            details.append(f"Duration: {record.duration}ms")
        if hasattr(record, 'ip'):
            details.append(f"IP: {record.ip}")
        
        if details:
            base_msg += f" | {' | '.join(details)}"
        
        # 添加参数
        if hasattr(record, 'params') and record.params:
            base_msg += f"\n  Params: {json.dumps(record.params, ensure_ascii=False)}"
        
        # 添加异常
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
        
        return base_msg


def setup_logging(
    log_dir: str = "logs",
    app_name: str = "fastapi_app",
    log_level: str = "INFO",
    json_format: bool = False,
    console_output: bool = True
):
    """
    配置日志系统
    
    Args:
        log_dir: 日志文件目录
        app_name: 应用名称，用于日志文件命名
        log_level: 日志级别
        json_format: 是否使用 JSON 格式
        console_output: 是否输出到控制台
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 选择格式化器
    formatter = JSONFormatter() if json_format else ReadableFormatter()
    
    # 文件处理器 - 按天轮转
    file_handler = TimedRotatingFileHandler(
        filename=log_path / f"{app_name}.log",
        when="midnight",  # 每天午夜轮转
        interval=1,
        backupCount=30,  # 保留30天
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"  # 日志文件后缀格式
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_handler = TimedRotatingFileHandler(
        filename=log_path / f"{app_name}_error.log",
        when="midnight",
        interval=1,
        backupCount=90,  # 错误日志保留90天
        encoding="utf-8"
    )
    error_handler.suffix = "%Y-%m-%d"
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            ReadableFormatter() if json_format else formatter
        )
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = None):
    """获取日志器"""
    return logging.getLogger(name or __name__)