import pytest
from benchmarks.native_cost import estimate


def test_cost_counts_cached_and_reasoning_tokens_once():
    assert estimate({"input_tokens": 1000, "cached_input_tokens": 600,
                     "cache_write_input_tokens": 100, "output_tokens": 100,
                     "reasoning_output_tokens": 80}) == pytest.approx(.00985)


@pytest.mark.parametrize("usage", [
    {"input_tokens": -1}, {"input_tokens": 2, "cached_input_tokens": 3},
    {"input_tokens": 272001}, {"input_tokens": 1.2},
])
def test_cost_refuses_invalid_or_out_of_scope_usage(usage):
    with pytest.raises(ValueError):
        estimate(usage)
