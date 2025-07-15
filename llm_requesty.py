import click
import llm
from llm.default_plugins.openai_models import Chat, AsyncChat
from pathlib import Path
from pydantic import Field
from typing import Optional
import json
import time
import httpx


def get_requesty_models():
    models = fetch_cached_json(
        url="https://router.requesty.ai/v1/models",
        path=llm.user_dir() / "requesty_models.json",
        cache_timeout=3600,
    )["data"]
    schema_supporting_ids = {
        model["id"]
        for model in fetch_cached_json(
            url="https://router.requesty.ai/v1/models?supported_parameters=structured_outputs",
            path=llm.user_dir() / "requesty_models_structured_outputs.json",
            cache_timeout=3600,
        )["data"]
    }
    # Annotate models with their schema support
    for model in models:
        model["supports_schema"] = model["id"] in schema_supporting_ids
    return models


class _mixin:
    class Options(Chat.Options):
        cache: Optional[bool] = Field(
            description="Use auto caching for this model",
            default=None,
        )

    def build_kwargs(self, prompt, stream):
        kwargs = super().build_kwargs(prompt, stream)
        kwargs.pop("cache", None)
        extra_body = {}
        if prompt.options.cache:
            extra_body["requesty"] = {
                "auto_cache": True
            }
        if extra_body:
            kwargs["extra_body"] = extra_body
        return kwargs


class requestyChat(_mixin, Chat):
    needs_key = "requesty"
    key_env_var = "requesty_KEY"

    def __str__(self):
        return "requesty: {}".format(self.model_id)


class requestyAsyncChat(_mixin, AsyncChat):
    needs_key = "requesty"
    key_env_var = "requesty_KEY"

    def __str__(self):
        return "requesty: {}".format(self.model_id)


@llm.hookimpl
def register_models(register):
    # Only do this if the requesty key is set
    key = llm.get_key("", "requesty", "requesty_KEY")
    if not key:
        return
    for model_definition in get_requesty_models():
        supports_images = get_supports_images(model_definition)
        kwargs = dict(
            model_id="requesty/{}".format(model_definition["id"]),
            model_name=model_definition["id"],
            vision=supports_images,
            supports_schema=model_definition["supports_schema"],
            api_base="https://router.requesty.ai/v1",
            headers={"HTTP-Referer": "https://llm.datasette.io/", "X-Title": "LLM"},
        )
        
        # Create model instances
        chat_model = requestyChat(**kwargs)
        async_chat_model = requestyAsyncChat(**kwargs)
        
        # Add attachment types for vision models
        if supports_images:
            chat_model.attachment_types = ["image/png", "image/jpeg", "image/gif", "image/webp"]
            async_chat_model.attachment_types = ["image/png", "image/jpeg", "image/gif", "image/webp"]
        
        register(chat_model, async_chat_model)


class DownloadError(Exception):
    pass


def fetch_cached_json(url, path, cache_timeout):
    path = Path(path)

    # Create directories if not exist
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        # Get the file's modification time
        mod_time = path.stat().st_mtime
        # Check if it's more than the cache_timeout old
        if time.time() - mod_time < cache_timeout:
            # If not, load the file
            with open(path, "r") as file:
                return json.load(file)

    # Try to download the data
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()  # This will raise an HTTPError if the request fails

        # If successful, write to the file
        with open(path, "w") as file:
            json.dump(response.json(), file)

        return response.json()
    except httpx.HTTPError:
        # If there's an existing file, load it
        if path.is_file():
            with open(path, "r") as file:
                return json.load(file)
        else:
            # If not, raise an error
            raise DownloadError(
                f"Failed to download data and no cache is available at {path}"
            )


def get_supports_images(model_definition):
    try:
        # Check if the model supports vision based on the supports_vision field
        if model_definition.get("supports_vision", False):
            return True
        
        # Fallback: check if the model name/ID contains vision-related keywords
        model_id = model_definition.get("id", "").lower()
        vision_keywords = ["vision", "visual", "multimodal", "vlm"]
        return any(keyword in model_id for keyword in vision_keywords)
    except Exception:
        return False


def refresh_models():
    """Refresh the cached models from the Requesty API"""
    key = llm.get_key("", "requesty", "requesty_KEY")
    if not key:
        raise click.ClickException("No key found for Requesty")
    
    headers = {"HTTP-Referer": "https://llm.datasette.io/", "X-Title": "LLM"}
    
    # Refresh main models cache
    try:
        response = httpx.get("https://router.requesty.ai/v1/models", headers=headers, follow_redirects=True)
        response.raise_for_status()
        models_data = response.json()
        
        models_path = llm.user_dir() / "requesty_models.json"
        models_path.parent.mkdir(parents=True, exist_ok=True)
        with open(models_path, "w") as file:
            json.dump(models_data, file, indent=2)
        
        models_count = len(models_data.get("data", []))
        click.echo(f"Refreshed {models_count} models cache at {models_path}", err=True)
        
    except httpx.HTTPError as e:
        raise click.ClickException(f"Failed to refresh models cache: {e}")
    
    # Refresh structured outputs models cache
    try:
        response = httpx.get(
            "https://router.requesty.ai/v1/models?supported_parameters=structured_outputs",
            headers=headers,
            follow_redirects=True
        )
        response.raise_for_status()
        structured_data = response.json()
        
        structured_path = llm.user_dir() / "requesty_models_structured_outputs.json"
        with open(structured_path, "w") as file:
            json.dump(structured_data, file, indent=2)
        
        structured_count = len(structured_data.get("data", []))
        click.echo(f"Refreshed {structured_count} structured outputs models cache at {structured_path}", err=True)
        
    except httpx.HTTPError as e:
        raise click.ClickException(f"Failed to refresh structured outputs cache: {e}")


@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def requesty():
        "Commands relating to the llm-requesty plugin"

    @requesty.command()
    def refresh():
        "Refresh the cached models from the Requesty API"
        refresh_models()

    @requesty.command()
    @click.option("json_", "--json", is_flag=True, help="Output as JSON")
    def models(json_):
        "List of requesty models"
        all_models = get_requesty_models()
        if json_:
            click.echo(json.dumps(all_models, indent=2))
        else:
            # Custom format
            for model in all_models:
                bits = []
                bits.append(f"- id: {model['id']}")
                # Use description as name if available, otherwise use id
                name = model.get('description', model['id'])
                bits.append(f"  name: {name}")
                context_length = model.get('context_window', 'N/A')
                if isinstance(context_length, int):
                    bits.append(f"  context_length: {context_length:,}")
                else:
                    bits.append(f"  context_length: {context_length}")
                bits.append(f"  supports_schema: {model['supports_schema']}")
                # Handle different pricing structure
                pricing_dict = {}
                if 'input_price' in model:
                    pricing_dict['input'] = model['input_price']
                if 'output_price' in model:
                    pricing_dict['output'] = model['output_price']
                pricing = format_pricing(pricing_dict) if pricing_dict else None
                if pricing:
                    bits.append("  pricing: " + pricing)
                click.echo("\n".join(bits) + "\n")



def format_price(key, price_str):
    """Format a price value with appropriate scaling and no trailing zeros."""
    price = float(price_str)

    if price == 0:
        return None

    # Determine scale based on magnitude
    if price < 0.0001:
        scale = 1000000
        suffix = "/M"
    elif price < 0.001:
        scale = 1000
        suffix = "/K"
    elif price < 1:
        scale = 1000
        suffix = "/K"
    else:
        scale = 1
        suffix = ""

    # Scale the price
    scaled_price = price * scale

    # Format without trailing zeros
    # Convert to string and remove trailing .0
    price_str = (
        f"{scaled_price:.10f}".rstrip("0").rstrip(".")
        if "." in f"{scaled_price:.10f}"
        else f"{scaled_price:.0f}"
    )

    return f"{key} ${price_str}{suffix}"


def format_pricing(pricing_dict):
    formatted_parts = []
    for key, value in pricing_dict.items():
        formatted_price = format_price(key, value)
        if formatted_price:
            formatted_parts.append(formatted_price)
    return ", ".join(formatted_parts)