"""
Kimi API Integration Layer for MasterBuilder7

Provides the interface to the Kimi API for actual agent execution.
Supports async operations, connection pooling, retry logic, caching,
and comprehensive error handling.

Usage:
    from apex.infrastructure.kimi_client import KimiClient
    
    client = KimiClient()
    response = await client.execute_task(
        agent_type="architect",
        task_input={"prompt": "Design a system..."},
        context={"project": "my-project"}
    )
"""

import os
import re
import json
import yaml
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import hashlib

import httpx
from pydantic import BaseModel, Field, ValidationError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kimi_client")


class ModelType(str, Enum):
    """Supported Kimi model types."""
    KIMI_K2_5 = "kimi-k2-5"           # Default for agents
    KIMI_K1_5 = "kimi-k1-5"           # For reasoning tasks
    KIMI_LATEST = "kimi-latest"       # Auto-updating latest model
    KIMI_MOONSHOT = "moonshot-v1-8k"  # Standard 8k context
    KIMI_MOONSHOT_32K = "moonshot-v1-32k"  # Extended context
    KIMI_MOONSHOT_128K = "moonshot-v1-128k"  # Maximum context


class TokenLimits:
    """Token limits for different models."""
    KIMI_K2_5 = {"max_tokens": 8192, "context_window": 256000}
    KIMI_K1_5 = {"max_tokens": 8192, "context_window": 128000}
    KIMI_LATEST = {"max_tokens": 8192, "context_window": 256000}
    MOONSHOT_V1_8K = {"max_tokens": 4096, "context_window": 8192}
    MOONSHOT_V1_32K = {"max_tokens": 8192, "context_window": 32768}
    MOONSHOT_V1_128K = {"max_tokens": 8192, "context_window": 131072}


class CostRates:
    """Cost per 1K tokens (in USD) - approximated rates."""
    KIMI_K2_5 = {"input": 0.003, "output": 0.015}
    KIMI_K1_5 = {"input": 0.005, "output": 0.025}
    KIMI_LATEST = {"input": 0.003, "output": 0.015}
    MOONSHOT_V1_8K = {"input": 0.006, "output": 0.012}
    MOONSHOT_V1_32K = {"input": 0.012, "output": 0.024}
    MOONSHOT_V1_128K = {"input": 0.024, "output": 0.048}


class ErrorType(Enum):
    """Types of errors for classification."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    SERVER_ERROR = "server_error"
    NETWORK = "network"
    UNKNOWN = "unknown"
    CONTENT_FILTER = "content_filter"
    CONTEXT_LENGTH = "context_length"


@dataclass
class TokenUsage:
    """Tracks token usage for requests."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    
    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            prompt_cache_hit_tokens=self.prompt_cache_hit_tokens + other.prompt_cache_hit_tokens,
            prompt_cache_miss_tokens=self.prompt_cache_miss_tokens + other.prompt_cache_miss_tokens,
        )


@dataclass
class CostEstimate:
    """Cost estimate for a request."""
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"


@dataclass
class AgentSpec:
    """Agent specification from YAML."""
    name: str
    role: str
    model: str = "kimi-k2-5"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    few_shot_examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of an agent execution."""
    success: bool
    output: Optional[Any] = None
    raw_response: str = ""
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    cost_estimate: CostEstimate = field(default_factory=CostEstimate)
    execution_time: float = 0.0
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    retry_count: int = 0


class KimiError(Exception):
    """Base exception for Kimi API errors."""
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN, 
                 status_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}


class KimiClient:
    """
    Async HTTP client for Kimi API with connection pooling,
    automatic retry, caching, and rate limiting.
    """
    
    # Default configuration
    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_TIMEOUT = 120
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RATE_LIMIT_RPM = 60
    DEFAULT_RATE_LIMIT_TPM = 60000
    
    # Retry configuration
    RETRY_BACKOFF_BASE = 2.0
    MAX_RETRY_DELAY = 60
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        rate_limit_rpm: Optional[int] = None,
        enable_caching: bool = True,
        cache_ttl: int = 300
    ):
        """
        Initialize the Kimi client.
        
        Args:
            api_key: Kimi API key (defaults to KIMI_API_KEY env var)
            base_url: API base URL (defaults to KIMI_BASE_URL or https://api.moonshot.cn/v1)
            timeout: Request timeout in seconds (defaults to KIMI_TIMEOUT or 120)
            max_retries: Max retry attempts (defaults to KIMI_MAX_RETRIES or 3)
            rate_limit_rpm: Rate limit in requests per minute (defaults to KIMI_RATE_LIMIT_RPM or 60)
            enable_caching: Whether to enable response caching
            cache_ttl: Cache TTL in seconds (default 300 = 5 minutes)
        """
        # Load configuration from environment or parameters
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise KimiError(
                "API key not provided. Set KIMI_API_KEY environment variable.",
                error_type=ErrorType.AUTHENTICATION
            )
        
        self.base_url = base_url or os.getenv("KIMI_BASE_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout or int(os.getenv("KIMI_TIMEOUT", self.DEFAULT_TIMEOUT))
        self.max_retries = max_retries or int(os.getenv("KIMI_MAX_RETRIES", self.DEFAULT_MAX_RETRIES))
        self.rate_limit_rpm = rate_limit_rpm or int(os.getenv("KIMI_RATE_LIMIT_RPM", self.DEFAULT_RATE_LIMIT_RPM))
        
        # HTTP client configuration
        self._client: Optional[httpx.AsyncClient] = None
        self._client_semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        # Rate limiting
        self._request_timestamps: List[datetime] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Caching
        self._enable_caching = enable_caching
        self._cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # Token usage tracking
        self._token_usage = TokenUsage()
        self._usage_lock = asyncio.Lock()
        
        # Available models
        self._available_models: Optional[List[str]] = None
        
        logger.info(f"KimiClient initialized with base_url={self.base_url}, timeout={self.timeout}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            timeout = httpx.Timeout(self.timeout, connect=10.0)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                limits=limits,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._client
    
    async def _check_rate_limit(self) -> float:
        """
        Check rate limit and return wait time if needed.
        
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        async with self._rate_limit_lock:
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=1)
            
            # Remove old timestamps
            self._request_timestamps = [
                ts for ts in self._request_timestamps if ts > window_start
            ]
            
            if len(self._request_timestamps) >= self.rate_limit_rpm:
                # Need to wait until oldest request falls outside window
                oldest = self._request_timestamps[0]
                wait_time = 60 - (now - oldest).total_seconds()
                return max(wait_time, 0.1)
            
            self._request_timestamps.append(now)
            return 0.0
    
    def _classify_error(self, error: Exception, status_code: Optional[int] = None) -> ErrorType:
        """Classify error type from exception and status code."""
        if status_code == 429:
            return ErrorType.RATE_LIMIT
        elif status_code in (401, 403):
            return ErrorType.AUTHENTICATION
        elif status_code == 400:
            return ErrorType.VALIDATION
        elif status_code and status_code >= 500:
            return ErrorType.SERVER_ERROR
        elif status_code == 413:
            return ErrorType.CONTEXT_LENGTH
        elif isinstance(error, httpx.TimeoutException):
            return ErrorType.TIMEOUT
        elif isinstance(error, httpx.NetworkError):
            return ErrorType.NETWORK
        elif isinstance(error, httpx.ConnectError):
            return ErrorType.NETWORK
        else:
            return ErrorType.UNKNOWN
    
    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.RETRY_BACKOFF_BASE ** retry_count,
            self.MAX_RETRY_DELAY
        )
        # Add jitter
        import random
        return delay * (0.5 + random.random())
    
    def _get_cache_key(self, messages: List[Dict], model: str, **kwargs) -> str:
        """Generate cache key from request parameters."""
        key_data = {
            "messages": messages,
            "model": model,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check if response is in cache and not expired."""
        if not self._enable_caching or cache_key not in self._cache:
            return None
        
        result, timestamp = self._cache[cache_key]
        if datetime.utcnow() - timestamp > timedelta(seconds=self._cache_ttl):
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Cache hit for key: {cache_key[:16]}...")
        return result
    
    def _set_cache(self, cache_key: str, response: Dict):
        """Store response in cache."""
        if self._enable_caching:
            self._cache[cache_key] = (response, datetime.utcnow())
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API health and connectivity.
        
        Returns:
            Dict with status, latency, and model availability
        """
        start_time = time.time()
        
        try:
            # Try to fetch models list as health check
            models = await self.get_available_models()
            latency = time.time() - start_time
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "available_models": len(models),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": self._classify_error(e).value,
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def get_available_models(self) -> List[str]:
        """
        Get list of available models from API.
        
        Returns:
            List of model IDs
        """
        if self._available_models is not None:
            return self._available_models
        
        client = await self._get_client()
        
        try:
            async with self._client_semaphore:
                response = await client.get("/models")
                response.raise_for_status()
                data = response.json()
                self._available_models = [m["id"] for m in data.get("data", [])]
                return self._available_models
        except Exception as e:
            # Fallback to known models if API fails
            logger.warning(f"Failed to fetch models, using defaults: {e}")
            return [m.value for m in ModelType]
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "kimi-k2-5",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        top_p: float = 1.0,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        use_cache: bool = True
    ) -> Union[Dict, AsyncGenerator[str, None]]:
        """
        Make a chat completion request to the Kimi API.
        
        Args:
            messages: List of message dicts with role and content
            model: Model to use
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            top_p: Nucleus sampling parameter
            presence_penalty: Presence penalty (-2 to 2)
            frequency_penalty: Frequency penalty (-2 to 2)
            use_cache: Whether to use response caching
        
        Returns:
            Response dict or async generator for streaming
        """
        # Check cache for non-streaming requests
        cache_key = None
        if use_cache and not stream and self._enable_caching:
            cache_key = self._get_cache_key(messages, model, temperature=temperature, max_tokens=max_tokens)
            cached = self._check_cache(cache_key)
            if cached:
                return cached
        
        # Get token limits for model
        limits = self._get_model_limits(model)
        if max_tokens is None:
            max_tokens = limits["max_tokens"]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
        }
        
        # Rate limiting
        wait_time = await self._check_rate_limit()
        if wait_time > 0:
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        client = await self._get_client()
        last_error = None
        
        for retry_count in range(self.max_retries + 1):
            try:
                async with self._client_semaphore:
                    if stream:
                        return self._stream_response(client, payload)
                    else:
                        response = await client.post("/chat/completions", json=payload)
                        response.raise_for_status()
                        data = response.json()
                        
                        # Track token usage
                        await self._track_usage(data.get("usage", {}))
                        
                        # Cache successful response
                        if cache_key:
                            self._set_cache(cache_key, data)
                        
                        return data
                        
            except httpx.HTTPStatusError as e:
                last_error = e
                error_type = self._classify_error(e, e.response.status_code)
                
                if error_type == ErrorType.RATE_LIMIT and retry_count < self.max_retries:
                    delay = self._calculate_backoff(retry_count)
                    logger.warning(f"Rate limit hit, retrying in {delay:.2f}s (attempt {retry_count + 1})")
                    await asyncio.sleep(delay)
                    continue
                elif error_type == ErrorType.SERVER_ERROR and retry_count < self.max_retries:
                    delay = self._calculate_backoff(retry_count)
                    logger.warning(f"Server error, retrying in {delay:.2f}s (attempt {retry_count + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise KimiError(
                        f"HTTP error: {e.response.status_code} - {e.response.text}",
                        error_type=error_type,
                        status_code=e.response.status_code
                    )
                    
            except httpx.TimeoutException as e:
                last_error = e
                if retry_count < self.max_retries:
                    delay = self._calculate_backoff(retry_count)
                    logger.warning(f"Timeout, retrying in {delay:.2f}s (attempt {retry_count + 1})")
                    await asyncio.sleep(delay)
                    continue
                raise KimiError(f"Request timeout after {self.timeout}s", error_type=ErrorType.TIMEOUT)
                
            except Exception as e:
                raise KimiError(f"Request failed: {str(e)}", error_type=self._classify_error(e))
        
        # All retries exhausted
        raise KimiError(
            f"Max retries ({self.max_retries}) exceeded. Last error: {last_error}",
            error_type=ErrorType.UNKNOWN
        )
    
    async def _stream_response(self, client: httpx.AsyncClient, payload: Dict) -> AsyncGenerator[str, None]:
        """Handle streaming response from API."""
        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
        except Exception as e:
            raise KimiError(f"Stream error: {str(e)}", error_type=self._classify_error(e))
    
    def _get_model_limits(self, model: str) -> Dict[str, int]:
        """Get token limits for a specific model."""
        limits_map = {
            ModelType.KIMI_K2_5: TokenLimits.KIMI_K2_5,
            ModelType.KIMI_K1_5: TokenLimits.KIMI_K1_5,
            ModelType.KIMI_LATEST: TokenLimits.KIMI_LATEST,
            ModelType.KIMI_MOONSHOT: TokenLimits.MOONSHOT_V1_8K,
            ModelType.KIMI_MOONSHOT_32K: TokenLimits.MOONSHOT_V1_32K,
            ModelType.KIMI_MOONSHOT_128K: TokenLimits.MOONSHOT_V1_128K,
        }
        return limits_map.get(model, TokenLimits.KIMI_K2_5)
    
    async def _track_usage(self, usage: Dict):
        """Track token usage."""
        async with self._usage_lock:
            self._token_usage.prompt_tokens += usage.get("prompt_tokens", 0)
            self._token_usage.completion_tokens += usage.get("completion_tokens", 0)
            self._token_usage.total_tokens += usage.get("total_tokens", 0)
            self._token_usage.prompt_cache_hit_tokens += usage.get("prompt_cache_hit_tokens", 0)
            self._token_usage.prompt_cache_miss_tokens += usage.get("prompt_cache_miss_tokens", 0)
    
    def get_token_usage(self) -> TokenUsage:
        """Get current token usage statistics."""
        return TokenUsage(
            prompt_tokens=self._token_usage.prompt_tokens,
            completion_tokens=self._token_usage.completion_tokens,
            total_tokens=self._token_usage.total_tokens,
            prompt_cache_hit_tokens=self._token_usage.prompt_cache_hit_tokens,
            prompt_cache_miss_tokens=self._token_usage.prompt_cache_miss_tokens,
        )
    
    def get_cost_estimate(self, model: Optional[str] = None, 
                         prompt_tokens: Optional[int] = None,
                         completion_tokens: Optional[int] = None) -> CostEstimate:
        """
        Get cost estimate based on token usage.
        
        Args:
            model: Model used (defaults to kimi-k2-5)
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        
        Returns:
            CostEstimate with input/output/total costs
        """
        model = model or "kimi-k2-5"
        
        rates = CostRates.KIMI_K2_5  # Default
        if model == ModelType.KIMI_K1_5:
            rates = CostRates.KIMI_K1_5
        elif "moonshot-v1-128k" in model:
            rates = CostRates.MOONSHOT_V1_128K
        elif "moonshot-v1-32k" in model:
            rates = CostRates.MOONSHOT_V1_32K
        elif "moonshot-v1-8k" in model:
            rates = CostRates.MOONSHOT_V1_8K
        
        # Use actual tracked tokens if not specified
        if prompt_tokens is None:
            prompt_tokens = self._token_usage.prompt_tokens
        if completion_tokens is None:
            completion_tokens = self._token_usage.completion_tokens
        
        input_cost = (prompt_tokens / 1000) * rates["input"]
        output_cost = (completion_tokens / 1000) * rates["output"]
        
        return CostEstimate(
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            total_cost=round(input_cost + output_cost, 6)
        )
    
    def _agent_spec_to_prompt(self, agent_spec: AgentSpec, context: Dict, 
                              task_input: Dict) -> Tuple[str, str]:
        """
        Convert agent spec YAML to system and user prompts.
        
        Args:
            agent_spec: Agent specification
            context: Execution context
            task_input: Task input
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Build system prompt
        system_parts = [
            f"You are {agent_spec.name}, a {agent_spec.role}.",
            "",
            "CAPABILITIES:",
        ]
        for cap in agent_spec.capabilities:
            system_parts.append(f"- {cap}")
        
        if agent_spec.tools:
            system_parts.extend(["", "AVAILABLE TOOLS:"])
            for tool in agent_spec.tools:
                system_parts.append(f"- {tool}")
        
        if agent_spec.system_prompt:
            system_parts.extend(["", agent_spec.system_prompt])
        
        system_prompt = "\n".join(system_parts)
        
        # Build user prompt
        user_parts = ["TASK:"]
        
        if isinstance(task_input, str):
            user_parts.append(task_input)
        elif isinstance(task_input, dict):
            user_parts.append(json.dumps(task_input, indent=2))
        else:
            user_parts.append(str(task_input))
        
        # Add context if provided
        if context:
            user_parts.extend(["", "CONTEXT:"])
            user_parts.append(json.dumps(context, indent=2))
        
        # Add few-shot examples if available
        if agent_spec.few_shot_examples:
            user_parts.extend(["", "EXAMPLES:"])
            for i, example in enumerate(agent_spec.few_shot_examples, 1):
                user_parts.append(f"\nExample {i}:")
                user_parts.append(f"Input: {example.get('input', '')}")
                user_parts.append(f"Output: {example.get('output', '')}")
        
        user_parts.extend([
            "",
            "Provide your response in a clear, structured format. If the task requires specific output format (JSON, YAML), use that format in a code block.",
        ])
        
        user_prompt = "\n".join(user_parts)
        
        return system_prompt, user_prompt
    
    def _parse_response(self, response: str) -> Any:
        """
        Parse YAML/JSON from markdown code blocks or plain text.
        
        Args:
            response: Raw response string
        
        Returns:
            Parsed data structure or raw string
        """
        # Try to extract code blocks
        code_block_pattern = r'```(?:json|yaml|yml)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            content = matches[-1]  # Use last code block
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(content)
                except yaml.YAMLError:
                    pass
        
        # Try to parse entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to parse as YAML
        try:
            return yaml.safe_load(response)
        except yaml.YAMLError:
            pass
        
        # Return as-is
        return response
    
    async def execute_agent(
        self,
        agent_spec: AgentSpec,
        context: Dict[str, Any],
        task_input: Union[str, Dict[str, Any]]
    ) -> ExecutionResult:
        """
        Execute an agent with the given spec and input.
        
        Args:
            agent_spec: Agent specification
            context: Execution context
            task_input: Task input (string or dict)
        
        Returns:
            ExecutionResult with output, usage, and metadata
        """
        start_time = time.time()
        
        try:
            # Convert spec to prompts
            system_prompt, user_prompt = self._agent_spec_to_prompt(
                agent_spec, context, task_input
            )
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Make API call
            response = await self.chat_completion(
                messages=messages,
                model=agent_spec.model,
                temperature=agent_spec.temperature,
                max_tokens=agent_spec.max_tokens
            )
            
            # Extract content
            content = response["choices"][0]["message"]["content"]
            
            # Parse response
            parsed_output = self._parse_response(content)
            
            # Get usage
            usage_data = response.get("usage", {})
            token_usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )
            
            # Calculate cost
            cost = self.get_cost_estimate(
                model=agent_spec.model,
                prompt_tokens=token_usage.prompt_tokens,
                completion_tokens=token_usage.completion_tokens
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=True,
                output=parsed_output,
                raw_response=content,
                token_usage=token_usage,
                cost_estimate=cost,
                execution_time=execution_time
            )
            
        except KimiError as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=e.error_type,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                error_type=ErrorType.UNKNOWN,
                execution_time=time.time() - start_time
            )
    
    async def stream_agent_response(
        self,
        agent_spec: AgentSpec,
        context: Dict[str, Any],
        task_input: Union[str, Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent response in real-time.
        
        Args:
            agent_spec: Agent specification
            context: Execution context
            task_input: Task input
        
        Yields:
            Text chunks as they arrive
        """
        # Convert spec to prompts
        system_prompt, user_prompt = self._agent_spec_to_prompt(
            agent_spec, context, task_input
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        stream = await self.chat_completion(
            messages=messages,
            model=agent_spec.model,
            temperature=agent_spec.temperature,
            max_tokens=agent_spec.max_tokens,
            stream=True
        )
        
        async for chunk in stream:
            yield chunk
    
    async def batch_execute(
        self,
        agents: List[AgentSpec],
        context: Dict[str, Any],
        task_inputs: List[Union[str, Dict[str, Any]]]
    ) -> List[ExecutionResult]:
        """
        Execute multiple agents in parallel.
        
        Args:
            agents: List of agent specifications
            context: Shared execution context
            task_inputs: List of task inputs (one per agent)
        
        Returns:
            List of ExecutionResults (in same order)
        """
        if len(agents) != len(task_inputs):
            raise ValueError("Number of agents must match number of task inputs")
        
        tasks = [
            self.execute_agent(agent, context, task_input)
            for agent, task_input in zip(agents, task_inputs)
        ]
        
        return await asyncio.gather(*tasks)
    
    def validate_agent_output(self, output: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate agent output against a JSON schema.
        
        Args:
            output: Parsed agent output
            schema: JSON schema dict
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from jsonschema import validate, ValidationError as JSONSchemaValidationError
            validate(instance=output, schema=schema)
            return True, None
        except ImportError:
            # Fallback to basic validation if jsonschema not available
            if not isinstance(output, dict):
                return False, f"Expected dict, got {type(output).__name__}"
            
            required = schema.get("required", [])
            for key in required:
                if key not in output:
                    return False, f"Missing required field: {key}"
            
            return True, None
        except JSONSchemaValidationError as e:
            return False, str(e)
    
    async def execute_task(
        self,
        agent_type: str,
        task_input: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute a task with a predefined agent type.
        
        Args:
            agent_type: Type of agent (architect, reviewer, etc.)
            task_input: Task input
            context: Optional execution context
        
        Returns:
            ExecutionResult
        """
        context = context or {}
        
        # Predefined agent specs
        agent_specs = {
            "architect": AgentSpec(
                name="System Architect",
                role="senior system architect specializing in distributed systems",
                model="kimi-k2-5",
                temperature=0.3,
                max_tokens=4096,
                capabilities=[
                    "Design scalable system architectures",
                    "Create data flow diagrams",
                    "Define API contracts",
                    "Recommend technology stacks"
                ],
                system_prompt="You design production-ready systems. Always provide clear, actionable designs with specific technology choices and architectural decisions."
            ),
            "reviewer": AgentSpec(
                name="Code Reviewer",
                role="senior code reviewer with security focus",
                model="kimi-k2-5",
                temperature=0.2,
                max_tokens=2048,
                capabilities=[
                    "Identify security vulnerabilities",
                    "Check code quality and best practices",
                    "Suggest optimizations",
                    "Review for maintainability"
                ],
                system_prompt="You are a thorough code reviewer. Focus on security, performance, and maintainability. Provide specific, actionable feedback."
            ),
            "writer": AgentSpec(
                name="Technical Writer",
                role="technical writer specializing in documentation",
                model="kimi-k2-5",
                temperature=0.5,
                max_tokens=4096,
                capabilities=[
                    "Write clear API documentation",
                    "Create user guides",
                    "Generate README files",
                    "Document architecture decisions"
                ],
                system_prompt="You write clear, comprehensive technical documentation. Use markdown formatting and include code examples."
            ),
            "tester": AgentSpec(
                name="Test Engineer",
                role="QA engineer specializing in test automation",
                model="kimi-k2-5",
                temperature=0.3,
                max_tokens=4096,
                capabilities=[
                    "Generate test cases",
                    "Write unit tests",
                    "Create integration test scenarios",
                    "Design load test plans"
                ],
                system_prompt="You create comprehensive test suites. Include edge cases, error scenarios, and performance tests. Output test code in appropriate format."
            ),
            "reasoning": AgentSpec(
                name="Reasoning Engine",
                role="analytical reasoning specialist",
                model="kimi-k1-5",
                temperature=0.2,
                max_tokens=8192,
                capabilities=[
                    "Complex problem analysis",
                    "Multi-step reasoning",
                    "Decision tree construction",
                    "Trade-off analysis"
                ],
                system_prompt="You provide deep analytical reasoning. Think step by step, consider multiple angles, and provide well-justified conclusions."
            ),
        }
        
        if agent_type not in agent_specs:
            return ExecutionResult(
                success=False,
                error=f"Unknown agent type: {agent_type}. Available: {list(agent_specs.keys())}",
                error_type=ErrorType.VALIDATION
            )
        
        agent_spec = agent_specs[agent_type]
        return await self.execute_agent(agent_spec, context, task_input)
    
    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("KimiClient connection closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# ============================================================================
# TEST / DEMO CODE
# ============================================================================

async def demo_health_check():
    """Demo: Health check endpoint."""
    print("\n" + "="*60)
    print("DEMO: Health Check")
    print("="*60)
    
    async with KimiClient() as client:
        health = await client.health_check()
        print(f"Status: {health['status']}")
        print(f"Latency: {health.get('latency_ms', 'N/A')}ms")
        print(f"Available Models: {health.get('available_models', 'N/A')}")
        print(f"Timestamp: {health['timestamp']}")


async def demo_chat_completion():
    """Demo: Basic chat completion."""
    print("\n" + "="*60)
    print("DEMO: Chat Completion")
    print("="*60)
    
    async with KimiClient() as client:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of South Africa?"}
        ]
        
        response = await client.chat_completion(
            messages=messages,
            model="kimi-k2-5",
            temperature=0.7,
            max_tokens=256
        )
        
        content = response["choices"][0]["message"]["content"]
        print(f"Response: {content}")
        
        usage = response.get("usage", {})
        print(f"\nToken Usage:")
        print(f"  Prompt: {usage.get('prompt_tokens', 0)}")
        print(f"  Completion: {usage.get('completion_tokens', 0)}")
        print(f"  Total: {usage.get('total_tokens', 0)}")


async def demo_agent_execution():
    """Demo: Agent execution with spec."""
    print("\n" + "="*60)
    print("DEMO: Agent Execution")
    print("="*60)
    
    async with KimiClient() as client:
        # Create agent spec
        spec = AgentSpec(
            name="API Designer",
            role="senior API designer",
            model="kimi-k2-5",
            temperature=0.3,
            max_tokens=1024,
            capabilities=[
                "Design RESTful APIs",
                "Define request/response schemas",
                "Specify error handling"
            ],
            system_prompt="Design production-ready REST APIs following best practices. Output your design in YAML format."
        )
        
        # Execute
        context = {
            "project": "E-commerce API",
            "version": "v2",
            "requirements": ["Authentication", "Rate limiting", "Pagination"]
        }
        
        task_input = "Design a product catalog API endpoint with filtering, sorting, and pagination"
        
        result = await client.execute_agent(spec, context, task_input)
        
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        
        if result.success:
            print(f"\nOutput:")
            print(json.dumps(result.output, indent=2) if isinstance(result.output, dict) else result.output)
            print(f"\nToken Usage: {result.token_usage.total_tokens} tokens")
            print(f"Estimated Cost: ${result.cost_estimate.total_cost:.6f}")
        else:
            print(f"Error: {result.error}")


async def demo_streaming():
    """Demo: Streaming response."""
    print("\n" + "="*60)
    print("DEMO: Streaming Response")
    print("="*60)
    
    async with KimiClient() as client:
        spec = AgentSpec(
            name="Story Writer",
            role="creative writer",
            model="kimi-k2-5",
            temperature=0.8,
            max_tokens=512,
            capabilities=["Write engaging stories"],
            system_prompt="Write creative, engaging short stories."
        )
        
        print("Streaming response: ", end="", flush=True)
        
        async for chunk in client.stream_agent_response(
            spec, {}, "Write a one-paragraph story about a developer discovering AI"
        ):
            print(chunk, end="", flush=True)
        
        print("\n")


async def demo_batch_execution():
    """Demo: Batch execution."""
    print("\n" + "="*60)
    print("DEMO: Batch Execution")
    print("="*60)
    
    async with KimiClient() as client:
        # Define agents and tasks
        agents = [
            AgentSpec(
                name="Fast Responder",
                role="quick responder",
                model="kimi-k2-5",
                temperature=0.5,
                max_tokens=100,
                capabilities=["Quick responses"]
            ),
            AgentSpec(
                name="Detail Provider",
                role="detail-oriented responder",
                model="kimi-k2-5",
                temperature=0.5,
                max_tokens=100,
                capabilities=["Detailed responses"]
            ),
        ]
        
        task_inputs = [
            "What is Python? (one sentence)",
            "What is Python? (one sentence)"
        ]
        
        context = {"topic": "programming"}
        
        print("Executing 2 agents in parallel...")
        results = await client.batch_execute(agents, context, task_inputs)
        
        for i, result in enumerate(results):
            print(f"\nAgent {i+1}:")
            print(f"  Success: {result.success}")
            if result.success:
                output = result.output[:100] + "..." if len(str(result.output)) > 100 else result.output
                print(f"  Output: {output}")
                print(f"  Tokens: {result.token_usage.total_tokens}")


async def demo_predefined_agents():
    """Demo: Using predefined agent types."""
    print("\n" + "="*60)
    print("DEMO: Predefined Agent Types")
    print("="*60)
    
    async with KimiClient() as client:
        # Test architect agent
        print("\n--- Architect Agent ---")
        result = await client.execute_task(
            agent_type="architect",
            task_input="Design a simple key-value store API",
            context={"scale": "millions of requests per day"}
        )
        
        if result.success:
            output_str = str(result.output)
            preview = output_str[:500] + "..." if len(output_str) > 500 else output_str
            print(preview)
        
        # Test reviewer agent
        print("\n--- Reviewer Agent ---")
        code_to_review = """
def process_payment(user_id, amount):
    query = f"UPDATE users SET balance = balance - {amount} WHERE id = {user_id}"
    db.execute(query)
        """
        result = await client.execute_task(
            agent_type="reviewer",
            task_input=f"Review this code:\n{code_to_review}",
            context={"language": "Python"}
        )
        
        if result.success:
            output_str = str(result.output)
            preview = output_str[:500] + "..." if len(output_str) > 500 else output_str
            print(preview)


async def demo_token_usage_and_cost():
    """Demo: Token usage tracking and cost estimation."""
    print("\n" + "="*60)
    print("DEMO: Token Usage & Cost Tracking")
    print("="*60)
    
    async with KimiClient() as client:
        # Make a few requests
        for i in range(3):
            await client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": f"Count from 1 to {i+3}"}
                ],
                model="kimi-k2-5",
                max_tokens=100
            )
        
        # Get usage stats
        usage = client.get_token_usage()
        cost = client.get_cost_estimate()
        
        print(f"Total Requests: 3")
        print(f"\nToken Usage:")
        print(f"  Prompt Tokens: {usage.prompt_tokens}")
        print(f"  Completion Tokens: {usage.completion_tokens}")
        print(f"  Total Tokens: {usage.total_tokens}")
        
        print(f"\nCost Estimate (USD):")
        print(f"  Input Cost: ${cost.input_cost:.6f}")
        print(f"  Output Cost: ${cost.output_cost:.6f}")
        print(f"  Total Cost: ${cost.total_cost:.6f}")


async def demo_error_handling():
    """Demo: Error handling and retry logic."""
    print("\n" + "="*60)
    print("DEMO: Error Handling")
    print("="*60)
    
    # This demo shows error handling without actually causing errors
    print("Error types handled by KimiClient:")
    for error_type in ErrorType:
        print(f"  - {error_type.value}")
    
    print("\nRetry configuration:")
    print(f"  Max Retries: {KimiClient.DEFAULT_MAX_RETRIES}")
    print(f"  Backoff Base: {KimiClient.RETRY_BACKOFF_BASE}")
    print(f"  Max Retry Delay: {KimiClient.MAX_RETRY_DELAY}s")


async def run_all_demos():
    """Run all demos."""
    # Check if API key is set
    if not os.getenv("KIMI_API_KEY"):
        print("="*60)
        print("WARNING: KIMI_API_KEY not set!")
        print("="*60)
        print("Set the environment variable to run live demos:")
        print("  export KIMI_API_KEY='your-api-key'")
        print("\nRunning in demo mode (showing structure only)...")
        print("="*60)
    
    try:
        # Run demos
        await demo_health_check()
        await demo_chat_completion()
        await demo_agent_execution()
        await demo_streaming()
        await demo_batch_execution()
        await demo_predefined_agents()
        await demo_token_usage_and_cost()
        await demo_error_handling()
        
        print("\n" + "="*60)
        print("All demos completed!")
        print("="*60)
        
    except KimiError as e:
        print(f"\nKimi API Error: {e}")
        print(f"Error Type: {e.error_type.value}")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_demos())
