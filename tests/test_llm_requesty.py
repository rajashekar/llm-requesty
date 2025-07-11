import llm
import pytest
from click.testing import CliRunner
from inline_snapshot import snapshot
from llm.cli import cli

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\xa6\x00\x00\x01\x1a"
    b"\x02\x03\x00\x00\x00\xe6\x99\xc4^\x00\x00\x00\tPLTE\xff\xff\xff"
    b"\x00\xff\x00\xfe\x01\x00\x12t\x01J\x00\x00\x00GIDATx\xda\xed\xd81\x11"
    b"\x000\x08\xc0\xc0.]\xea\xaf&Q\x89\x04V\xe0>\xf3+\xc8\x91Z\xf4\xa2\x08EQ\x14E"
    b"Q\x14EQ\x14EQ\xd4B\x91$I3\xbb\xbf\x08EQ\x14EQ\x14EQ\x14E\xd1\xa5"
    b"\xd4\x17\x91\xc6\x95\x05\x15\x0f\x9f\xc5\t\x9f\xa4\x00\x00\x00\x00IEND\xaeB`"
    b"\x82"
)


@pytest.mark.vcr
def test_prompt():
    model = llm.get_model("requesty/google/gemini-2.5-pro")
    response = model.prompt("Two names for a pet pelican, be brief")
    assert len(str(response)) > 0
    response_dict = dict(response.response_json)
    response_dict.pop("id", None)  # differs between requests
    # Basic structure validation
    assert "content" in response_dict
    assert "role" in response_dict
    assert response_dict["role"] == "assistant"


@pytest.mark.vcr
def test_llm_models():
    runner = CliRunner()
    result = runner.invoke(cli, ["models", "list"])
    assert result.exit_code == 0, result.output
    fragments = (
        "requesty: requesty/deepinfra/meta-llama/Meta-Llama-3.1-405B-Instruct",
        "requesty: requesty/deepinfra/Qwen/Qwen2.5-72B-Instruct",
    )
    for fragment in fragments:
        assert fragment in result.output


@pytest.mark.vcr
def test_image_prompt():
    model = llm.get_model("requesty/google/gemini-2.5-pro")
    response = model.prompt(
        "Describe image in three words",
        attachments=[llm.Attachment(content=TINY_PNG)],
    )
    assert len(str(response)) > 0
    response_dict = response.response_json
    response_dict.pop("id", None)  # differs between requests
    # Basic structure validation
    assert "content" in response_dict
    assert "role" in response_dict
    assert response_dict["role"] == "assistant"


@pytest.mark.vcr
def test_requesty_models_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["requesty", "models"])
    assert result.exit_code == 0, result.output
    # Check for expected model format
    assert "- id: deepinfra/meta-llama/Meta-Llama-3.1-405B-Instruct" in result.output
    assert "context_length:" in result.output
    assert "supports_schema:" in result.output
    assert "pricing:" in result.output


@pytest.mark.vcr
def test_requesty_models_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["requesty", "models", "--json"])
    assert result.exit_code == 0, result.output
    # Should be valid JSON
    import json
    models = json.loads(result.output)
    assert isinstance(models, list)
    assert len(models) > 0
    # Check first model has expected structure
    first_model = models[0]
    assert "id" in first_model
    assert "supports_schema" in first_model


def test_cache_option():
    """Test that the cache option is properly handled"""
    model = llm.get_model("requesty/google/gemini-2.5-pro")
    # Test that cache option doesn't cause errors
    prompt = model.prompt("Hello", cache=True)
    # This mainly tests that the option is accepted without error


def test_get_supports_images():
    """Test the vision detection function"""
    from llm_requesty import get_supports_images
    
    # Test with vision support
    vision_model = {"supports_vision": True}
    assert get_supports_images(vision_model) == True
    
    # Test without vision support
    text_model = {"supports_vision": False}
    assert get_supports_images(text_model) == False
    
    # Test with missing field
    incomplete_model = {}
    assert get_supports_images(incomplete_model) == False


def test_format_pricing():
    """Test the pricing formatting function"""
    from llm_requesty import format_pricing
    
    pricing_dict = {
        "input": 0.0000008,
        "output": 0.0000008
    }
    result = format_pricing(pricing_dict)
    assert "input $0.8/M" in result
    assert "output $0.8/M" in result
    
    # Test with zero pricing
    zero_pricing = {
        "input": 0,
        "output": 0.001
    }
    result = format_pricing(zero_pricing)
    assert "output $1/K" in result
    assert "input" not in result  # Zero prices should be filtered out


def test_model_registration():
    """Test that models are properly registered"""
    # This test verifies that the plugin registers models correctly
    models = [m for m in llm.get_models() if m.model_id.startswith("requesty/")]
    assert len(models) > 0
    
    # Check that a known model is registered
    model_ids = [m.model_id for m in models]
    assert any("deepinfra/meta-llama" in model_id for model_id in model_ids)


def test_model_string_representation():
    """Test the string representation of models"""
    from llm_requesty import requestyChat
    
    model = requestyChat(
        model_id="requesty/test-model",
        model_name="test-model"
    )
    assert str(model) == "requesty: requesty/test-model"