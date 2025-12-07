"""
自定义中间件：节流请求日志输出
"""
import time
from datetime import datetime
from django.utils.deprecation import MiddlewareMixin

# 全局变量：记录上次打印日志的时间
_last_request_log_time = {}
_log_interval = 1.0  # 每秒最多打印一次


class ThrottledRequestLoggingMiddleware(MiddlewareMixin):
    """
    节流请求日志输出的中间件
    对于频繁的请求（如 /update_environment/），每秒最多打印一次日志
    """
    
    def process_response(self, request, response):
        # 只处理特定路径的请求
        if request.path == '/update_environment/':
            current_time = time.time()
            last_time = _last_request_log_time.get(request.path, 0)
            
            # 如果距离上次打印超过1秒，则打印日志
            if current_time - last_time >= _log_interval:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] [Request] {request.method} {request.path} {response.status_code} {len(response.content)} bytes")
                _last_request_log_time[request.path] = current_time
            # 否则静默处理（不打印）
        
        return response

