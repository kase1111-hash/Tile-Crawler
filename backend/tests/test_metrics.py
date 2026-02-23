"""Tests for metrics.py — LLM latency measurement decorator and context manager."""

import asyncio
import logging
import pytest

from metrics import timed_llm_call, LLMTimer


class TestTimedLLMCall:
    """Tests for the timed_llm_call decorator."""

    @pytest.mark.asyncio
    async def test_decorator_returns_result(self):
        @timed_llm_call(label="test_func")
        async def my_func():
            return "hello"

        result = await my_func()
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_name(self):
        @timed_llm_call(label="test_func")
        async def my_func():
            pass

        assert my_func.__name__ == "my_func"

    @pytest.mark.asyncio
    async def test_decorator_logs_success(self, caplog):
        @timed_llm_call(label="generate_room")
        async def my_func():
            return 42

        with caplog.at_level(logging.INFO, logger="llm_latency"):
            await my_func()

        assert any("generate_room" in r.message and "completed" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_decorator_logs_failure(self, caplog):
        @timed_llm_call(label="broken_call")
        async def failing_func():
            raise ValueError("boom")

        with caplog.at_level(logging.WARNING, logger="llm_latency"):
            with pytest.raises(ValueError, match="boom"):
                await failing_func()

        assert any("broken_call" in r.message and "failed" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_decorator_uses_function_name_when_no_label(self):
        @timed_llm_call()
        async def custom_name():
            return True

        assert custom_name.__name__ == "custom_name"
        result = await custom_name()
        assert result is True

    @pytest.mark.asyncio
    async def test_decorator_passes_args(self):
        @timed_llm_call(label="with_args")
        async def add(a, b):
            return a + b

        result = await add(3, 4)
        assert result == 7

    @pytest.mark.asyncio
    async def test_decorator_passes_kwargs(self):
        @timed_llm_call(label="with_kwargs")
        async def greet(name="world"):
            return f"hello {name}"

        result = await greet(name="test")
        assert result == "hello test"


class TestLLMTimer:
    """Tests for the LLMTimer context manager."""

    def test_timer_measures_elapsed(self):
        import time

        with LLMTimer("test_timer") as timer:
            time.sleep(0.05)

        assert timer.elapsed >= 0.04  # allow small margin
        assert timer.elapsed < 1.0  # sanity

    def test_timer_label_stored(self):
        timer = LLMTimer("my_label")
        assert timer.label == "my_label"

    def test_timer_default_label(self):
        timer = LLMTimer()
        assert timer.label == "llm_call"

    def test_timer_logs_success(self, caplog):
        with caplog.at_level(logging.INFO, logger="llm_latency"):
            with LLMTimer("success_timer"):
                pass

        assert any("success_timer" in r.message and "completed" in r.message for r in caplog.records)

    def test_timer_logs_failure(self, caplog):
        with caplog.at_level(logging.WARNING, logger="llm_latency"):
            with pytest.raises(ZeroDivisionError):
                with LLMTimer("error_timer"):
                    _ = 1 / 0

        assert any("error_timer" in r.message and "failed" in r.message for r in caplog.records)

    def test_timer_does_not_suppress_exceptions(self):
        with pytest.raises(RuntimeError, match="test error"):
            with LLMTimer("no_suppress"):
                raise RuntimeError("test error")

    def test_timer_elapsed_zero_before_use(self):
        timer = LLMTimer()
        assert timer.elapsed == 0.0
