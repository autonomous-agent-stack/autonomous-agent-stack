# AI + RPA 企业级集成实战（第二阶段）- 补充章节（7-15）

---

## 7. 日志管理系统

### 7.1 Loki 日志聚合

#### 7.1.1 Loki 配置

```yaml
# loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    max_transfer_retries: 0
  chunk_idle_period: 1h
  chunk_block_size: 262144
  chunk_retain_period: 1m
  max_transfer_age: 30m

schema_config:
  configs:
  - from: 2020-10-24
    store: boltdb-shipper
    object_store: filesystem
    schema: v11
    index:
      prefix: index_
      period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s

compactor:
  working_directory: /loki/boltdb-shipper-compactor
  shared_store: filesystem
```

#### 7.1.2 Promtail 日志采集

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Kubernetes Pods 日志
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels:
      - __meta_kubernetes_pod_label_app
      target_label: app
    - source_labels:
      - __meta_kubernetes_pod_label_component
      target_label: component
    - source_labels:
      - __meta_kubernetes_pod_name
      target_label: pod
    - source_labels:
      - __meta_kubernetes_namespace
      target_label: namespace
    - source_labels:
      - __meta_kubernetes_pod_node_name
      target_label: node
    - source_labels:
      - __meta_kubernetes_pod_label_release
      target_label: release
    - source_labels:
      - __address__
      target_label: __path__
      replacement: /var/log/pods/*$1*/*/*.log
      separator: /
    - source_labels:
      - __meta_kubernetes_pod_uid
      target_label: __path__
      replacement: /var/log/pods/*$1*/*/*.log
      separator: /

  # 容器日志
  - job_name: containers
    static_configs:
    - targets:
        - localhost
      labels:
        job: containerlogs
        __path__: /var/log/containers/*.log

# 自定义 Pipeline
pipeline_stages:
  - json:
      expressions:
        time: time
        level: level
        msg: message
        service: service_name
        trace_id: trace_id
  - labels:
      level:
      service:
      trace_id:
  - output:
      source: msg
```

#### 7.1.3 结构化日志

```python
# src/logging_config.py
import logging
import json
from datetime import datetime
from typing import Dict, Any
import traceback


class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "trace_id": getattr(record, "trace_id", ""),
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stacktrace": traceback.format_exception(*record.exc_info)
            }
        
        # 添加自定义字段
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # 文件输出
    file_handler = logging.FileHandler(f'/app/logs/{service_name}.log')
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    return logger


# 使用示例
import structlog

# 结构化日志
log = structlog.get_logger()

log.info(
    "request_started",
    service="parser",
    trace_id="abc123",
    endpoint="/convert",
    user_id="user456"
)

log.error(
    "request_failed",
    service="parser",
    trace_id="abc123",
    error_type="ValueError",
    error_message="Invalid input",
    extra_fields={
        "input_data": {"text": "hello"},
        "retry_count": 3
    }
)
```

### 7.2 ELK Stack 集成

#### 7.2.1 Elasticsearch 配置

```yaml
# elasticsearch.yml
cluster.name: "ai-rpa-cluster"
node.name: "es-node-1"
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node

# 索引设置
index.number_of_shards: 3
index.number_of_replicas: 1

# 安全设置
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true

# 索引生命周期管理
xpack.ilm.enabled: true
```

#### 7.2.2 Logstash 配置

```conf
# logstash.conf
input {
  beats {
    port => 5044
  }
  
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["ai-rpa-logs"]
    codec => json
  }
}

filter {
  # JSON 解析
  json {
    source => "message"
  }
  
  # 添加时间戳
  date {
    match => ["timestamp", "ISO8601"]
  }
  
  # Grok 解析
  grok {
    match => {
      "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}"
    }
  }
  
  # 添加环境标签
  mutate {
    add_field => {
      "environment" => "${ENV:ENVIRONMENT,production}"
    }
  }
  
  # 删除不需要的字段
  mutate {
    remove_field => ["message"]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "ai-rpa-%{+YYYY.MM.dd}"
    user => "${ELASTIC_USER}"
    password => "${ELASTIC_PASSWORD}"
  }
  
  # 调试输出
  stdout {
    codec => rubydebug
  }
}
```

#### 7.2.3 Kibana Dashboard

```json
{
  "version": "7.15.0",
  "objects": [
    {
      "type": "index-pattern",
      "id": "ai-rpa-*",
      "attributes": {
        "title": "ai-rpa-*",
        "timeFieldName": "timestamp",
        "fields": "[{\"name\":\"@timestamp\",\"type\":\"date\",\"searchable\":true,\"aggregatable\":true},{\"name\":\"level\",\"type\":\"string\"},{\"name\":\"service\",\"type\":\"string\"},{\"name\":\"trace_id\",\"type\":\"string\"}]"
      }
    },
    {
      "type": "dashboard",
      "id": "ai-rpa-logs-dashboard",
      "attributes": {
        "title": "AI + RPA Platform - Logs",
        "panelsJSON": "[{\"gridData\":{\"x\":0,\"y\":0,\"w\":48,\"h\":15},\"version\":\"7.15.0\",\"panelIndex\":\"1\",\"type\":\"visualization\",\"embeddableConfig\":{},\"panelRefName\":\"panel_0\"}]"
      }
    }
  ]
}
```

---

## 8. 错误处理机制

### 8.1 重试机制

```python
# src/retry.py
import time
import random
from functools import wraps
from typing import Callable, Type, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """重试失败异常"""
    pass


class RetryStrategy:
    """重试策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_retries:
            return False
        
        return isinstance(exception, self.exceptions)


# 预定义重试策略
RETRY_STRATEGIES = {
    "default": RetryStrategy(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        backoff_factor=2.0
    ),
    "aggressive": RetryStrategy(
        max_retries=5,
        base_delay=0.5,
        max_delay=5.0,
        backoff_factor=1.5
    ),
    "conservative": RetryStrategy(
        max_retries=2,
        base_delay=2.0,
        max_delay=30.0,
        backoff_factor=3.0
    ),
    "llm_api": RetryStrategy(
        max_retries=3,
        base_delay=2.0,
        max_delay=60.0,
        backoff_factor=2.0,
        exceptions=(ConnectionError, TimeoutError)
    ),
    "rpa_execution": RetryStrategy(
        max_retries=2,
        base_delay=5.0,
        max_delay=30.0,
        backoff_factor=2.0
    )
}


def retry(
    strategy_name: str = "default",
    strategy: Optional[RetryStrategy] = None,
    on_retry: Optional[Callable] = None
):
    """重试装饰器"""
    if strategy is None:
        strategy = RETRY_STRATEGIES[strategy_name]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, strategy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except strategy.exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt}/{strategy.max_retries} failed for {func.__name__}: {str(e)}"
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    if not strategy.should_retry(attempt + 1, e):
                        break
                    
                    delay = strategy.get_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
            
            # 所有重试都失败
            logger.error(
                f"All {strategy.max_retries} attempts failed for {func.__name__}"
            )
            raise RetryError(f"Function {func.__name__} failed after {strategy.max_retries} retries") from last_exception
        
        return wrapper
    return decorator


# 使用示例
@retry(strategy_name="llm_api", on_retry=lambda attempt, e: logger.info(f"LLM API error: {e}"))
def call_llm_api(prompt: str) -> str:
    """调用 LLM API"""
    # 模拟 API 调用
    response = requests.post(
        "https://api.example.com/v1/completions",
        json={"prompt": prompt}
    )
    response.raise_for_status()
    return response.json()["text"]


@retry(strategy=RetryStrategy(max_retries=5, base_delay=0.1))
def execute_rpa_step(step_id: str):
    """执行 RPA 步骤"""
    # 执行逻辑
    pass
```

### 8.2 熔断机制

```python
# src/circuit_breaker.py
import time
from enum import Enum
from typing import Callable, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常，允许请求
    OPEN = "open"          # 熔断，拒绝请求
    HALF_OPEN = "half_open"  # 半开，允许测试请求


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
    
    def call(self, func: Callable, *args, **kwargs):
        """执行函数（带熔断保护）"""
        if self.state == CircuitState.OPEN:
            # 检查是否可以尝试恢复
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            # 设置超时
            result = func(*args, **kwargs)
            
            # 成功
            self._on_success()
            return result
        
        except Exception as e:
            # 失败
            self._on_failure()
            raise
    
    def _on_success(self):
        """处理成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.failure_count = 0
                logger.info("Circuit breaker transitioned to CLOSED")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """处理失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker transitioned to OPEN (test failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state


class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass


# 全局熔断器注册表
CIRCUIT_BREAKERS = {
    "llm_api": CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
    "rpa_executor": CircuitBreaker(failure_threshold=3, recovery_timeout=120.0),
    "database": CircuitBreaker(failure_threshold=10, recovery_timeout=30.0),
    "cache": CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)
}


def circuit_breaker(name: str):
    """熔断器装饰器"""
    cb = CIRCUIT_BREAKERS[name]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


# 使用示例
@circuit_breaker("llm_api")
def call_llm_with_protection(prompt: str) -> str:
    """带熔断保护的 LLM 调用"""
    return call_llm_api(prompt)
```

### 8.3 降级策略

```python
# src/degradation.py
from typing import Callable, Optional, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class DegradationStrategy(ABC):
    """降级策略基类"""
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """执行降级逻辑"""
        pass


class FallbackStrategy(DegradationStrategy):
    """回退策略"""
    
    def __init__(self, fallback_func: Callable):
        self.fallback_func = fallback_func
    
    def execute(self, *args, **kwargs) -> Any:
        logger.info("Executing fallback strategy")
        return self.fallback_func(*args, **kwargs)


class CacheStrategy(DegradationStrategy):
    """缓存策略"""
    
    def __init__(self, cache_key: str, cache_client):
        self.cache_key = cache_key
        self.cache_client = cache_client
    
    def execute(self, *args, **kwargs) -> Any:
        logger.info(f"Returning cached value for key: {self.cache_key}")
        cached_value = self.cache_client.get(self.cache_key)
        
        if cached_value is None:
            raise DegradationError(f"No cached value for key: {self.cache_key}")
        
        return cached_value


class DefaultResponseStrategy(DegradationStrategy):
    """默认响应策略"""
    
    def __init__(self, default_value: Any):
        self.default_value = default_value
    
    def execute(self, *args, **kwargs) -> Any:
        logger.warning(f"Returning default value: {self.default_value}")
        return self.default_value


class DegradationError(Exception):
    """降级异常"""
    pass


def with_degradation(
    degradation_strategy: Optional[DegradationStrategy] = None,
    exception_types: tuple = (Exception,)
):
    """降级装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                logger.error(f"Function {func.__name__} failed: {e}")
                
                if degradation_strategy is not None:
                    try:
                        return degradation_strategy.execute(*args, **kwargs)
                    except Exception as de:
                        logger.error(f"Degradation strategy failed: {de}")
                        raise DegradationError("Both main function and degradation strategy failed") from de
                else:
                    raise
        
        return wrapper
    return decorator


# 使用示例
# 1. 回退策略
@with_degradation(
    degradation_strategy=FallbackStrategy(
        fallback_func=lambda prompt: f"Mock response for: {prompt}"
    )
)
def llm_generate_with_fallback(prompt: str) -> str:
    return call_llm_api(prompt)


# 2. 缓存策略
@with_degradation(
    degradation_strategy=CacheStrategy(
        cache_key="flow:123",
        cache_client=redis_client
    )
)
def get_flow_with_cache(flow_id: str):
    return load_flow_from_db(flow_id)


# 3. 默认响应策略
@with_degradation(
    degradation_strategy=DefaultResponseStrategy(default_value="Service unavailable")
)
def get_health_status():
    return check_external_service()
```

### 8.4 异常分类和处理

```python
# src/exceptions.py
from enum import Enum


class ErrorCode(Enum):
    """错误代码枚举"""
    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_INPUT = 1001
    MISSING_PARAMETER = 1002
    INVALID_FORMAT = 1003
    
    # LLM API 错误 (2000-2999)
    LLM_API_ERROR = 2000
    LLM_API_TIMEOUT = 2001
    LLM_API_RATE_LIMIT = 2002
    LLM_API_QUOTA_EXCEEDED = 2003
    LLM_INVALID_RESPONSE = 2004
    
    # RPA 执行错误 (3000-3999)
    RPA_EXECUTION_FAILED = 3000
    RPA_TIMEOUT = 3001
    RPA_FLOW_NOT_FOUND = 3002
    RPA_STEP_FAILED = 3003
    RPA_VALIDATION_ERROR = 3004
    
    # 数据库错误 (4000-4999)
    DATABASE_ERROR = 4000
    DATABASE_CONNECTION_ERROR = 4001
    DATABASE_QUERY_ERROR = 4002
    DATABASE_TRANSACTION_ERROR = 4003
    
    # 服务错误 (5000-5999)
    SERVICE_UNAVAILABLE = 5000
    SERVICE_TIMEOUT = 5001
    SERVICE_OVERLOAD = 5002


class AppException(Exception):
    """应用异常基类"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[dict] = None,
        cause: Optional[Exception] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": self.message,
            "details": self.details
        }


class LLMException(AppException):
    """LLM 异常"""
    pass


class RPAException(AppException):
    """RPA 异常"""
    pass


class DatabaseException(AppException):
    """数据库异常"""
    pass


class ServiceException(AppException):
    """服务异常"""
    pass


# 异常处理器
class ExceptionHandler:
    """异常处理器"""
    
    @staticmethod
    def handle(exception: Exception) -> dict:
        """处理异常并返回响应"""
        if isinstance(exception, AppException):
            return {
                "error": exception.to_dict(),
                "status_code": ExceptionHandler._get_status_code(exception.error_code)
            }
        else:
            # 未知异常
            return {
                "error": {
                    "error_code": ErrorCode.UNKNOWN_ERROR.value,
                    "error_name": ErrorCode.UNKNOWN_ERROR.name,
                    "message": "An unexpected error occurred"
                },
                "status_code": 500
            }
    
    @staticmethod
    def _get_status_code(error_code: ErrorCode) -> int:
        """根据错误代码获取 HTTP 状态码"""
        if error_code in [
            ErrorCode.INVALID_INPUT,
            ErrorCode.MISSING_PARAMETER,
            ErrorCode.INVALID_FORMAT,
            ErrorCode.RPA_VALIDATION_ERROR
        ]:
            return 400
        
        if error_code in [
            ErrorCode.RPA_FLOW_NOT_FOUND
        ]:
            return 404
        
        if error_code in [
            ErrorCode.LLM_API_RATE_LIMIT,
            ErrorCode.SERVICE_OVERLOAD
        ]:
            return 429
        
        if error_code in [
            ErrorCode.SERVICE_UNAVAILABLE
        ]:
            return 503
        
        return 500


# 使用示例
try:
    result = call_llm_api(prompt)
except ConnectionError as e:
    raise LLMException(
        error_code=ErrorCode.LLM_API_TIMEOUT,
        message="LLM API timeout",
        details={"timeout": 30},
        cause=e
    )
```

---

## 9. 成本优化策略

### 9.1 LLM API 成本优化

#### 9.1.1 Token 使用优化

```python
# src/llm_optimizer.py
from typing import List, Dict, Optional
import tiktoken
import logging

logger = logging.getLogger(__name__)


class LLMMetrics:
    """LLM 指标"""
    
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_request(self, input_tokens: int, output_tokens: int, cache_hit: bool = False):
        """记录请求"""
        self.requests += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_requests": self.requests,
            "total_input_tokens": self.input_tokens,
            "total_output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "avg_input_tokens": self.input_tokens / self.requests if self.requests > 0 else 0,
            "avg_output_tokens": self.output_tokens / self.requests if self.requests > 0 else 0,
            "cache_hit_rate": self.cache_hits / self.requests if self.requests > 0 else 0,
            "estimated_cost": self._estimate_cost()
        }
    
    def _estimate_cost(self) -> float:
        """估算成本（假设价格）"""
        # GLM-4 价格示例
        INPUT_PRICE = 0.001 / 1000  # 每 1000 token 的价格
        OUTPUT_PRICE = 0.002 / 1000
        
        return (
            self.input_tokens * INPUT_PRICE +
            self.output_tokens * OUTPUT_PRICE
        )


class LLMPromptOptimizer:
    """LLM 提示优化器"""
    
    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.metrics = LLMMetrics()
    
    def optimize_prompt(
        self,
        prompt: str,
        max_tokens: int = 4096,
        instructions: Optional[str] = None
    ) -> str:
        """优化提示词"""
        # 1. 计算当前 token 数
        current_tokens = len(self.encoder.encode(prompt))
        
        if current_tokens <= max_tokens:
            return prompt
        
        # 2. 如果超过限制，尝试压缩
        logger.warning(f"Prompt too long ({current_tokens} tokens), compressing...")
        
        # 移除多余的空格和换行
        compressed = ' '.join(prompt.split())
        compressed_tokens = len(self.encoder.encode(compressed))
        
        if compressed_tokens <= max_tokens:
            return compressed
        
        # 3. 截断到最大长度（保留重要部分）
        tokens = self.encoder.encode(prompt)
        truncated = self.encoder.decode(tokens[:max_tokens])
        
        logger.warning(f"Prompt truncated to {max_tokens} tokens")
        return truncated
    
    def estimate_tokens(self, text: str) -> int:
        """估算 token 数"""
        return len(self.encoder.encode(text))
    
    def batch_request(
        self,
        prompts: List[str],
        model: str,
        max_batch_size: int = 10
    ) -> List[str]:
        """批量请求（减少 API 调用次数）"""
        results = []
        
        for i in range(0, len(prompts), max_batch_size):
            batch = prompts[i:i+max_batch_size]
            # 批量调用逻辑
            # ...
            pass
        
        return results


class LLMCache:
    """LLM 响应缓存"""
    
    def __init__(self, cache_client):
        self.cache_client = cache_client
        self.metrics = LLMMetrics()
    
    def get(self, prompt: str) -> Optional[str]:
        """从缓存获取响应"""
        cache_key = self._get_cache_key(prompt)
        cached = self.cache_client.get(cache_key)
        
        if cached:
            self.metrics.cache_hits += 1
            logger.info(f"Cache hit for prompt (first 50 chars): {prompt[:50]}...")
            return cached
        
        self.metrics.cache_misses += 1
        return None
    
    def set(self, prompt: str, response: str, ttl: int = 3600):
        """设置缓存"""
        cache_key = self._get_cache_key(prompt)
        self.cache_client.set(cache_key, response, ex=ttl)
    
    def _get_cache_key(self, prompt: str) -> str:
        """生成缓存键"""
        import hashlib
        return f"llm:response:{hashlib.md5(prompt.encode()).hexdigest()}"
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.metrics.cache_hits + self.metrics.cache_misses
        return self.metrics.cache_hits / total if total > 0 else 0


# 智能路由
class LLMRouter:
    """LLM 路由器（根据任务复杂度选择模型）"""
    
    def __init__(self):
        self.routes = {
            "simple": {"model": "glm-4-flash", "max_tokens": 2048, "cost_factor": 0.5},
            "medium": {"model": "glm-4", "max_tokens": 4096, "cost_factor": 1.0},
            "complex": {"model": "glm-4-turbo", "max_tokens": 8192, "cost_factor": 2.0}
        }
    
    def route(self, task: str, prompt: str) -> str:
        """根据任务选择模型"""
        # 分析任务复杂度
        complexity = self._analyze_complexity(task, prompt)
        
        # 选择合适的模型
        route = self.routes[complexity]
        model = route["model"]
        
        logger.info(f"Routing task '{task}' to model '{model}' (complexity: {complexity})")
        
        return model
    
    def _analyze_complexity(self, task: str, prompt: str) -> str:
        """分析任务复杂度"""
        # 简单启发式规则
        if len(prompt) < 500 and task in ["intent_classification", "entity_extraction"]:
            return "simple"
        elif len(prompt) < 2000:
            return "medium"
        else:
            return "complex"


# 使用示例
optimizer = LLMPromptOptimizer()
cache = LLMCache(redis_client)
router = LLMRouter()

prompt = "Convert this requirement to RPA flow..."
optimized_prompt = optimizer.optimize_prompt(prompt, max_tokens=4096)

# 检查缓存
cached_response = cache.get(prompt)
if cached_response:
    response = cached_response
else:
    # 选择模型
    model = router.route("code_generation", prompt)
    
    # 调用 LLM
    response = call_llm_api(optimized_prompt, model=model)
    
    # 缓存响应
    cache.set(prompt, response)
```

#### 9.1.2 成本监控

```python
# src/cost_monitor.py
from datetime import datetime, timedelta
from typing import Dict, List
import json


class CostMonitor:
    """成本监控"""
    
    # 模型价格（每 1000 tokens，单位：美元）
    MODEL_PRICES = {
        "glm-4-flash": {"input": 0.0005, "output": 0.001},
        "glm-4": {"input": 0.001, "output": 0.002},
        "glm-4-turbo": {"input": 0.002, "output": 0.004},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
    }
    
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        service: str,
        operation: str
    ):
        """记录使用情况"""
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "service": service,
            "operation": operation
        }
        
        self.storage.save(record)
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        prices = self.MODEL_PRICES.get(model)
        if not prices:
            logger.warning(f"Unknown model: {model}, using default prices")
            prices = self.MODEL_PRICES["glm-4"]
        
        input_cost = (input_tokens / 1000) * prices["input"]
        output_cost = (output_tokens / 1000) * prices["output"]
        
        return input_cost + output_cost
    
    def get_daily_cost(self, date: datetime) -> Dict:
        """获取每日成本"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        records = self.storage.query(start, end)
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_cost": sum(r["cost"] for r in records),
            "total_tokens": sum(r["total_tokens"] for r in records),
            "total_requests": len(records),
            "by_model": self._group_by_model(records),
            "by_service": self._group_by_service(records)
        }
    
    def get_cost_trend(self, days: int = 30) -> List[Dict]:
        """获取成本趋势"""
        trend = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            daily_cost = self.get_daily_cost(date)
            trend.append(daily_cost)
        
        return trend
    
    def _group_by_model(self, records: List[Dict]) -> Dict:
        """按模型分组"""
        groups = {}
        
        for r in records:
            model = r["model"]
            if model not in groups:
                groups[model] = {
                    "cost": 0,
                    "tokens": 0,
                    "requests": 0
                }
            
            groups[model]["cost"] += r["cost"]
            groups[model]["tokens"] += r["total_tokens"]
            groups[model]["requests"] += 1
        
        return groups
    
    def _group_by_service(self, records: List[Dict]) -> Dict:
        """按服务分组"""
        groups = {}
        
        for r in records:
            service = r["service"]
            if service not in groups:
                groups[service] = {
                    "cost": 0,
                    "tokens": 0,
                    "requests": 0
                }
            
            groups[service]["cost"] += r["cost"]
            groups[service]["tokens"] += r["total_tokens"]
            groups[service]["requests"] += 1
        
        return groups
    
    def check_budget(self, monthly_budget: float) -> Dict:
        """检查预算"""
        today = datetime.utcnow()
        first_day = today.replace(day=1)
        
        # 计算本月累计成本
        monthly_cost = 0
        current_date = first_day
        
        while current_date <= today:
            daily = self.get_daily_cost(current_date)
            monthly_cost += daily["total_cost"]
            current_date += timedelta(days=1)
        
        # 预估月度成本
        days_in_month = (today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1)).day
        days_elapsed = today.day
        avg_daily_cost = monthly_cost / days_elapsed if days_elapsed > 0 else 0
        estimated_monthly_cost = avg_daily_cost * days_in_month
        
        return {
            "monthly_budget": monthly_budget,
            "current_spend": monthly_cost,
            "estimated_total": estimated_monthly_cost,
            "budget_used": monthly_cost / monthly_budget if monthly_budget > 0 else 0,
            "is_over_budget": estimated_monthly_cost > monthly_budget,
            "remaining_days": days_in_month - days_elapsed
        }


# 使用示例
cost_monitor = CostMonitor(storage_backend)

# 记录使用
cost_monitor.record_usage(
    model="glm-4",
    input_tokens=500,
    output_tokens=300,
    service="parser",
    operation="intent_classification"
)

# 检查预算
budget_check = cost_monitor.check_budget(monthly_budget=1000.0)

if budget_check["is_over_budget"]:
    logger.warning(f"Budget warning: Estimated cost ${budget_check['estimated_total']:.2f} exceeds budget ${budget_check['monthly_budget']:.2f}")
    # 可以触发告警或降级策略
```

### 9.2 资源调度优化

#### 9.2.1 自动扩缩容策略

```yaml
# HPA 配置 - 基于多个指标
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-rpa-platform-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-rpa-platform
  minReplicas: 3
  maxReplicas: 20
  metrics:
  # CPU 使用率
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  
  # 内存使用率
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  
  # 自定义指标 - 请求速率
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  
  # 自定义指标 - 队列长度
  - type: Pods
    pods:
      metric:
        name: queue_length
      target:
        type: AverageValue
        averageValue: "50"
  
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 5
        periodSeconds: 30
      selectPolicy: Max
```

#### 9.2.2 垂直自动扩缩容 (VPA)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ai-rpa-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-rpa-platform
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: ai-parser
      minAllowed:
        cpu: "100m"
        memory: "256Mi"
      maxAllowed:
        cpu: "4000m"
        memory: "8Gi"
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
    - containerName: ai-generator
      minAllowed:
        cpu: "100m"
        memory: "256Mi"
      maxAllowed:
        cpu: "4000m"
        memory: "8Gi"
    - containerName: ai-executor
      minAllowed:
        cpu: "200m"
        memory: "512Mi"
      maxAllowed:
        cpu: "8000m"
        memory: "16Gi"
```

#### 9.2.3 节点自动扩缩容 (Cluster Autoscaler)

```yaml
# Cluster Autoscaler 配置
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-system-pods=false
        - --scale-down-enabled=true
        - --scale-down-unneeded-time=10m
        - --scale-down-delay-after-add=10m
        - --scale-down-delay-after-delete=10s
        - --balance-similar-node-groups=true
        - --expander=least-waste
        env:
        - name: AWS_REGION
          value: us-west-2
```

### 9.3 缓存策略

```python
# src/cache.py
from typing import Optional, Callable, Any, Dict
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class CacheStrategy:
    """缓存策略"""
    
    def __init__(
        self,
        cache_client,
        default_ttl: int = 3600,
        key_prefix: str = "cache"
    ):
        self.cache_client = cache_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.metrics = {
            "hits": 0,
            "misses": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._build_key(key)
        value = self.cache_client.get(cache_key)
        
        if value:
            self.metrics["hits"] += 1
            logger.debug(f"Cache hit: {key}")
            return json.loads(value)
        
        self.metrics["misses"] += 1
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        cache_key = self._build_key(key)
        serialized = json.dumps(value)
        ttl = ttl or self.default_ttl
        self.cache_client.set(cache_key, serialized, ex=ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str):
        """删除缓存"""
        cache_key = self._build_key(key)
        self.cache_client.delete(cache_key)
        logger.debug(f"Cache deleted: {key}")
    
    def _build_key(self, key: str) -> str:
        """构建缓存键"""
        return f"{self.key_prefix}:{key}"
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.metrics["hits"] + self.metrics["misses"]
        return {
            "hits": self.metrics["hits"],
            "misses": self.metrics["misses"],
            "hit_rate": self.metrics["hits"] / total if total > 0 else 0
        }


def cached(
    cache_strategy: CacheStrategy,
    ttl: Optional[int] = None,
    key_generator: Optional[Callable] = None
):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_value = cache_strategy.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_strategy.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


# 多级缓存
class MultiLevelCache:
    """多级缓存（L1: 本地内存，L2: Redis）"""
    
    def __init__(self, l1_size: int = 1000, l2_client=None):
        from collections import OrderedDict
        
        self.l1_cache = OrderedDict()
        self.l1_size = l1_size
        self.l2_client = l2_client
        self.metrics = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存（多级）"""
        # L1: 本地缓存
        if key in self.l1_cache:
            self.metrics["l1_hits"] += 1
            self.l1_cache.move_to_end(key)
            return self.l1_cache[key]
        
        self.metrics["l1_misses"] += 1
        
        # L2: Redis 缓存
        if self.l2_client:
            value = self.l2_client.get(key)
            if value:
                self.metrics["l2_hits"] += 1
                decoded = json.loads(value)
                
                # 回填 L1
                self._set_l1(key, decoded)
                return decoded
        
        self.metrics["l2_misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存（多级）"""
        # L1
        self._set_l1(key, value)
        
        # L2
        if self.l2_client:
            serialized = json.dumps(value)
            if ttl:
                self.l2_client.set(key, serialized, ex=ttl)
            else:
                self.l2_client.set(key, serialized)
    
    def _set_l1(self, key: str, value: Any):
        """设置 L1 缓存"""
        if len(self.l1_cache) >= self.l1_size:
            self.l1_cache.popitem(last=False)
        self.l1_cache[key] = value
    
    def invalidate(self, key: str):
        """失效缓存"""
        if key in self.l1_cache:
            del self.l1_cache[key]
        if self.l2_client:
            self.l2_client.delete(key)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_requests = (
            self.metrics["l1_hits"] + self.metrics["l1_misses"] +
            self.metrics["l2_hits"] + self.metrics["l2_misses"]
        )
        
        return {
            "l1_cache_size": len(self.l1_cache),
            "l1_hit_rate": self.metrics["l1_hits"] / (self.metrics["l1_hits"] + self.metrics["l1_misses"]) if (self.metrics["l1_hits"] + self.metrics["l1_misses"]) > 0 else 0,
            "l2_hit_rate": self.metrics["l2_hits"] / (self.metrics["l2_hits"] + self.metrics["l2_misses"]) if (self.metrics["l2_hits"] + self.metrics["l2_misses"]) > 0 else 0,
            "overall_hit_rate": (self.metrics["l1_hits"] + self.metrics["l2_hits"]) / total_requests if total_requests > 0 else 0
        }


# 使用示例
cache = CacheStrategy(redis_client, default_ttl=3600)
multi_cache = MultiLevelCache(l1_size=1000, l2_client=redis_client)

# 缓存装饰器
@cached(cache_strategy=cache, ttl=600)
def get_flow_definition(flow_id: str):
    return load_flow_from_db(flow_id)

# 多级缓存
def get_flow_with_multilevel(flow_id: str):
    cached = multi_cache.get(flow_id)
    if cached:
        return cached
    
    flow = load_flow_from_db(flow_id)
    multi_cache.set(flow_id, flow, ttl=3600)
    return flow
```

---

(由于篇幅限制，第10-15章节继续在下一个文件中)

---

## 章节说明

补充章节 7-9 涵盖：

**第7章：日志管理系统**
- Loki 日志聚合配置
- Promtail 日志采集
- 结构化日志（JSON 格式）
- ELK Stack 集成（Elasticsearch、Logstash、Kibana）

**第8章：错误处理机制**
- 重试机制（指数退避、抖动）
- 熔断机制（Circuit Breaker 模式）
- 降级策略（回退、缓存、默认响应）
- 异常分类和处理

**第9章：成本优化策略**
- LLM API 成本优化（Token 优化、缓存、智能路由）
- 成本监控（日成本、月成本趋势、预算检查）
- 资源调度优化（HPA、VPA、Cluster Autoscaler）
- 缓存策略（多级缓存、缓存装饰器）

---

**状态**: 已完成第7-9章  
**待完成**: 第10-15章（SLA管理、灾备恢复、安全加固、运维自动化、案例研究、最佳实践）
