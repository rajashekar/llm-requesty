# llm-requesty

[![PyPI](https://img.shields.io/pypi/v/llm-requesty.svg)](https://pypi.org/project/llm-requesty/)
[![Changelog](https://img.shields.io/github/v/release/rajashekar/llm-requesty?include_prereleases&label=changelog)](https://github.com/rajashekar/llm-requesty/releases)
[![Tests](https://github.com/rajashekar/llm-requesty/workflows/Test/badge.svg)](https://github.com/rajashekar/llm-requesty/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/rajashekar/llm-requesty/blob/main/LICENSE)

[LLM](https://llm.datasette.io/) plugin for models hosted by [Requesty](https://requesty.ai/)

## Installation

First, [install the LLM command-line utility](https://llm.datasette.io/en/stable/setup.html).

Now install this plugin in the same environment as LLM.
```bash
llm install llm-requesty
```

## Configuration

You will need an API key from Requesty. You can [obtain one here](https://requesty.ai/keys).

You can set that as an environment variable called `requesty_KEY`, or add it to the `llm` set of saved keys using:

```bash
llm keys set requesty
```
```
Enter key: <paste key here>
```

## Usage

To list available models, run:
```bash
llm models list
```
You should see a list that looks something like this:
```
requesty: requesty/deepinfra/meta-llama/Meta-Llama-3.1-405B-Instruct
requesty: requesty/deepinfra/Qwen/Qwen2.5-72B-Instruct
requesty: requesty/deepinfra/meta-llama/Llama-3.3-70B-Instruct
...
```

In requesty, you need to approve the models you want to use before you can prompt them. You can do this by running:
Click on [Admin Panel](https://app.requesty.ai/admin-panel?tab=models) and  then user "Add Model" to add the models you want to use.


To run a prompt against a model, pass its full model ID to the `-m` option, like this:
```bash
llm -m requesty/google/gemini-2.5-flash-lite-preview-06-17 "Five spooky names for a pet tarantula"
```

You can set a shorter alias for a model using the `llm aliases` command like so:
```bash
llm aliases set llama3.3 requesty/deepinfra/meta-llama/Llama-3.3-70B-Instruct
```
Now you can prompt the model using:
```bash
cat llm_requesty.py | llm -m llama3.3 -s 'write some pytest tests for this'
```

### Vision models

Some Requesty models can accept image attachments. Run this command:

```bash
llm models --options -q requesty
```
And look for models that list these attachment types:

```
  Attachment types:
    application/pdf, image/gif, image/jpeg, image/png, image/webp
```

You can feed these models images as URLs or file paths, for example:

```bash
curl https://static.simonwillison.net/static/2024/pelicans.jpg | llm \
    -m requesty/google/gemini-2.5-pro 'describe this image' -a -
```


### Auto caching

Requesty supports auto caching to improve response times and reduce costs for repeated requests. Enable this feature using the `-o cache 1` option:

```bash
llm -m requesty/deepinfra/meta-llama/Llama-3.3-70B-Instruct -o cache 1 'explain quantum computing'
```

### Listing models

The `llm models -q requesty` command will display all available models, or you can use this command to see more detailed information:

```bash
llm requesty models
```
Output starts like this:
```yaml
- id: deepinfra/meta-llama/Meta-Llama-3.1-405B-Instruct
  name: A lightweight and ultra-fast variant of Llama 3.3 70B, for use when quick response times are needed most.
  context_length: 130,815
  supports_schema: True
  pricing: input $0.8/M, output $0.8/M

- id: deepinfra/Qwen/Qwen2.5-72B-Instruct
  name: Qwen3, the latest generation in the Qwen large language model series...
  context_length: 131,072
  supports_schema: True
  pricing: input $0.23/M, output $0.4/M
```

Add `--json` to get back JSON instead:
```bash
llm requesty models --json
```

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-requesty
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
llm install -e '.[test]'
```
To run the tests:
```bash
pytest
```
To update recordings and snapshots, run:
```bash
PYTEST_REQUESTY_KEY="$(llm keys get requesty)" \
  pytest --record-mode=rewrite --inline-snapshot=fix