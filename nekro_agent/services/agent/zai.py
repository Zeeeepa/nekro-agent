import json
import time
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Union,
)

import aiofiles
from pydantic import BaseModel

from nekro_agent.core import logger
from zai_sdk.client import ZAIClient
from zai_sdk.models import ChatCompletionResponse, StreamingChunk

from .creator import OpenAIChatMessage


class ZAIResponse(BaseModel):
    response_content: str  # 最终的回复内容
    thought_chain: str  # 思考链
    messages: List[Dict[str, Any]]  # 原始消息列表
    message_cnt: int  # 消息数量
    token_consumption: int  # 总 token 消耗（估算值）
    token_input: int  # 输入 token 消耗（估算值）
    token_output: int  # 输出 token 消耗（估算值）
    use_model: str  # 使用的模型
    speed_tokens_per_second: float  # token 生成速度 / 秒
    first_token_cost_ms: int  # 首 token 生成时间
    generation_time_ms: int  # 总生成时间
    stream_mode: bool  # 是否为流式模式
    log_path: Optional[Union[str, Path]] = None  # 日志文件路径

    def gen_log(self, lang: str = "zh") -> str:
        """生成日志"""
        if lang == "zh":
            return (
                f"[ZAI{'-Stream' if self.stream_mode else ''}] 使用模型: {self.use_model}\n"
                f"总 token 消耗: {self.token_consumption}\n"
                f"输入 token: {self.token_input}\n"
                f"输出 token: {self.token_output}\n"
                f"总生成时间: {self.generation_time_ms}ms\n"
                f"生成速度: {self.speed_tokens_per_second} tokens/s\n"
                f"首 token 生成时间: {self.first_token_cost_ms}ms\n"
            )
        return (
            f"[ZAI{'-Stream' if self.stream_mode else ''}] Use model: {self.use_model}\n"
            f"Total token consumption: {self.token_consumption}\n"
            f"Input token: {self.token_input}\n"
            f"Output token: {self.token_output}\n"
            f"Total generation time: {self.generation_time_ms}ms\n"
            f"Token generation speed: {self.speed_tokens_per_second} tokens/s\n"
            f"First token cost: {self.first_token_cost_ms}ms\n"
        )

    def price_consumption(self, base_rate: float = 1, completion_rate: float = 1, token_price: float = 1) -> float:
        """计算价格"""
        return (self.token_input * base_rate + self.token_output * base_rate * completion_rate) * token_price

    def _generate_json_log(
        self,
        messages: Any,
        message_cnt: int,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """生成JSON格式的日志内容"""
        return {
            "timestamp": datetime.now().isoformat(),
            "model": self.use_model,
            "stream_mode": self.stream_mode,
            "metrics": {
                "token_consumption": self.token_consumption,
                "token_input": self.token_input,
                "token_output": self.token_output,
                "generation_time_ms": self.generation_time_ms,
                "speed_tokens_per_second": self.speed_tokens_per_second,
                "first_token_cost_ms": self.first_token_cost_ms,
                "message_cnt": message_cnt,
            },
            "request": {
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            },
            "response": {"content": self.response_content, "thought_chain": self.thought_chain},
        }

    def _generate_text_log(
        self,
        messages: Any,
        message_cnt: int,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """生成文本格式的日志内容"""
        log_content = [
            f"--- ZAI调用日志 [{datetime.now().isoformat()}] ---",
            f"模型: {self.use_model} {'(流式)' if self.stream_mode else ''}",
            f"消息数量: {message_cnt}",
            f"Token消耗: 总计={self.token_consumption}, 输入={self.token_input}, 输出={self.token_output}",
            f"生成时间: {self.generation_time_ms}ms, 首token时间: {self.first_token_cost_ms}ms",
            f"生成速度: {self.speed_tokens_per_second:.2f} tokens/s",
            f"生成参数: temp={temperature}, top_p={top_p}, max_tokens={max_tokens}",
            "-----------------------------------\n",
            "请求详情:",
        ]

        # 添加请求消息内容，使用<|role|>格式
        for _, msg in enumerate(messages):
            try:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # 处理混合 content 类型
                if isinstance(content, list):
                    processed_content = []
                    for item in content:
                        item_type = item.get("type", "unknown")

                        if item_type == "text":
                            # 文本类型，直接添加内容
                            text_content = item.get("text", "")
                            processed_content.append(text_content)

                        elif item_type == "image_url":
                            # 图片URL类型，简化显示
                            image_url = item.get("image_url", {}).get("url", "")
                            if len(image_url) > 128:
                                # 截取前60个和后60个字符，中间用...连接
                                truncated_url = f"{image_url[:60]}...{image_url[-60:]}"
                                processed_content.append(f"[图片] {truncated_url}")
                            else:
                                processed_content.append(f"[图片] {image_url}")

                        else:
                            # 其他类型
                            processed_content.append(f"[{item_type}] {str(item)[:100]}...")

                    # 合并处理后的内容
                    log_content.append(f"<|{role}|>\n" + "\n".join(processed_content) + "\n")
                else:
                    # 处理普通字符串内容
                    log_content.append(f"<|{role}|>\n{content}\n")
            except Exception as e:
                log_content.append(f"<|unknown|>\n处理消息时出错: {str(e)[:100]}...\n原始消息: {str(msg)[:100]}...")

        log_content.append("\n-----------------------------------\n")

        # 添加响应内容
        log_content.extend(
            [
                "思考链:",
                f"{self.thought_chain or '<Empty>'}",
                "-----------------------------------\n",
                "响应内容:",
                f"<|assistant|>\n{self.response_content or '<Empty>'}",
                "-----------------------------------\n",
            ],
        )

        return "\n".join(log_content)

    async def save_log(
        self,
        log_path: Union[str, Path],
        log_style: Literal["json", "text", "auto"] = "auto",
        messages: Any = None,
        message_cnt: int = 0,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> bool:
        """保存日志到文件"""
        if not log_path:
            return False

        path: Path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if log_style == "auto":
            log_style = "json" if path.suffix == ".json" else "text"

        if log_style == "json":
            log_data = self._generate_json_log(
                messages,
                message_cnt,
                temperature,
                top_p,
                max_tokens,
            )
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(
                        log_data,
                        ensure_ascii=False,
                        default=lambda o: str(o) if not isinstance(o, (dict, list, str, int, float, bool, type(None))) else o,
                    )
                    + "\n",
                )
        else:
            log_text = self._generate_text_log(
                messages,
                message_cnt,
                temperature,
                top_p,
                max_tokens,
            )
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(log_text)

        return True


class ZAIErrResponse(ZAIResponse):
    error_msg: str  # 错误信息

    @classmethod
    def create_from_exception(
        cls,
        e: Exception,
        use_model: str,
        stream_mode: bool,
        messages: List[Dict[str, Any]],
        log_path: Optional[Union[str, Path]] = None,
    ) -> "ZAIErrResponse":
        return cls(
            response_content="",
            thought_chain="",
            messages=messages,
            message_cnt=0,
            token_consumption=0,
            token_input=0,
            token_output=0,
            use_model=use_model,
            speed_tokens_per_second=0,
            first_token_cost_ms=0,
            generation_time_ms=0,
            stream_mode=stream_mode,
            log_path=log_path,
            error_msg=str(e),
        )


class ZAIStreamChunk(BaseModel):
    chunk_text: str  # 当前生成的文本
    thought_chain: str  # 当前的思考链
    token_consumption: int  # 当前token消耗（估算值）
    token_input: int  # 当前输入token消耗（估算值）
    token_output: int  # 当前输出token消耗（估算值）


_AsyncFunc = Callable[..., Coroutine[Any, Any, ZAIStreamChunk]]


def _estimate_token_count(text: str) -> int:
    """简单的token数量估算，1个token约等于4个字符"""
    return len(text) // 4 + 1


async def gen_zai_chat_response(
    model: str,
    messages: Any,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    stream_mode: bool = False,
    max_wait_time: Optional[int] = None,
    enable_thinking: bool = True,
    chunk_callback: Optional[_AsyncFunc] = None,
    log_path: Optional[Union[str, Path]] = None,
    error_log_path: Optional[Union[str, Path]] = None,
    log_style: Literal["json", "text", "auto"] = "auto",
) -> ZAIResponse:
    """生成聊天回复内容"""

    _start_time: float = time.time()

    # messages 处理
    messages = [msg.to_dict() if isinstance(msg, OpenAIChatMessage) else msg for msg in messages]

    output: str = ""
    thought_chain: str = ""
    token_consumption: int = 0
    token_input: int = 0
    token_output: int = 0
    first_token_time: Optional[float] = None

    try:
        # 初始化ZAI客户端
        client = ZAIClient(
            token=api_key,
            base_url=base_url or "https://chat.z.ai",
            timeout=max_wait_time or 180,
            auto_auth=not bool(api_key),  # 如果没有提供API密钥，则使用自动认证
            verbose=False,
        )

        # 估算输入token数量
        input_text = " ".join([str(msg.get("content", "")) for msg in messages])
        token_input = _estimate_token_count(input_text)

        if stream_mode:
            # 创建临时聊天会话
            chat = client.create_chat(
                title="Nekro Agent Chat",
                models=[model],
                enable_thinking=enable_thinking,
            )

            # 流式生成
            chunk_count = 0
            async for chunk in client.stream_completion(
                chat_id=chat.id,
                messages=messages,
                model=model,
                enable_thinking=enable_thinking,
            ):
                if not first_token_time and chunk.delta_content:
                    first_token_time = time.time()

                if chunk.phase == "answer" and chunk.delta_content:
                    output += chunk.delta_content
                    chunk_count += 1

                if chunk.phase == "thinking" and chunk.delta_content:
                    thought_chain += chunk.delta_content

                # 估算当前token消耗
                current_token_output = _estimate_token_count(output)
                current_token_consumption = token_input + current_token_output

                if chunk_callback and await chunk_callback(
                    ZAIStreamChunk(
                        chunk_text=chunk.delta_content or "",
                        thought_chain=chunk.delta_content if chunk.phase == "thinking" else "",
                        token_consumption=current_token_consumption,
                        token_input=token_input,
                        token_output=current_token_output,
                    ),
                ):
                    break

        else:
            # 非流式生成
            response = client.simple_chat(
                message=messages[-1].get("content", "") if messages else "",
                model=model,
                enable_thinking=enable_thinking,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )

            output = response.content
            thought_chain = response.thinking or ""

        # 估算最终token数量
        token_output = _estimate_token_count(output)
        token_consumption = token_input + token_output

    except Exception as e:
        logger.exception(f"ZAI请求失败: {e}")
        response = ZAIErrResponse.create_from_exception(
            e,
            use_model=model,
            stream_mode=stream_mode,
            messages=messages,
            log_path=error_log_path,
        )
        if error_log_path:
            await response.save_log(
                log_path=error_log_path,
                log_style=log_style,
                messages=messages,
                message_cnt=len(messages) + 1,
            )
        raise

    # 时间统计
    _end_time: float = time.time()
    _generation_time_ms: int = int((_end_time - _start_time) * 1000)
    _speed_tokens_per_second: float = token_output / (_generation_time_ms / 1000) if _generation_time_ms > 0 else 0
    _first_token_cost_ms: Optional[int] = None
    if first_token_time:
        _first_token_cost_ms = int((first_token_time - _start_time) * 1000)

    response = ZAIResponse(
        response_content=output,
        thought_chain=thought_chain,
        messages=messages,
        message_cnt=len(messages) + 1,
        token_consumption=token_consumption,
        token_input=token_input,
        token_output=token_output,
        use_model=model,
        speed_tokens_per_second=_speed_tokens_per_second,
        first_token_cost_ms=_first_token_cost_ms or 0,
        generation_time_ms=_generation_time_ms,
        stream_mode=stream_mode,
        log_path=log_path,
    )

    if log_path:
        await response.save_log(
            log_path=log_path,
            log_style=log_style,
            messages=messages,
            message_cnt=len(messages) + 1,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    return response


async def gen_zai_chat_stream(
    model: str,
    messages: List[Union[OpenAIChatMessage, Dict[str, Any]]],
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    enable_thinking: bool = True,
) -> AsyncGenerator[str, None]:
    """简化的ZAI流式生成器，直接产生文本片段

    这是一个简化版的流式生成器，直接返回生成的文本片段，而不是复杂的ZAIResponse对象。
    适用于需要简单流式输出的场景，如网页UI中的实时代码生成。

    Args:
        model: 模型名称
        messages: 消息列表，可以是OpenAIChatMessage对象或字典
        base_url: ZAI基础URL
        api_key: ZAI API密钥
        temperature: 温度参数，控制随机性
        top_p: Top-p采样
        max_tokens: 最大生成token数
        enable_thinking: 是否启用思考模式

    Yields:
        生成的文本片段
    """
    logger.info(f"启动简化的ZAI流式生成，使用模型: {model}")

    # 处理消息格式
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, OpenAIChatMessage):
            formatted_messages.append(msg.to_dict())
        else:
            formatted_messages.append(msg)

    try:
        # 初始化ZAI客户端
        client = ZAIClient(
            token=api_key,
            base_url=base_url or "https://chat.z.ai",
            timeout=180,
            auto_auth=not bool(api_key),  # 如果没有提供API密钥，则使用自动认证
            verbose=False,
        )

        # 创建临时聊天会话
        chat = client.create_chat(
            title="Nekro Agent Stream Chat",
            models=[model],
            enable_thinking=enable_thinking,
        )

        # 流式生成并直接产生文本片段
        async for chunk in client.stream_completion(
            chat_id=chat.id,
            messages=formatted_messages,
            model=model,
            enable_thinking=enable_thinking,
        ):
            if chunk.phase == "answer" and chunk.delta_content:
                yield chunk.delta_content

    except Exception as e:
        logger.error(f"ZAI流式生成过程中出错: {e}")
        raise