# https://platform.moonshot.ai/docs/guide/kimi-k2-6-quickstart
# extracted 2026-10-15T10:57:10.114761Z

> Documentation IndexFetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

...

# Kimi K2.6
## Quick Start
### Multimodal Tool Capability Example
```python theme={null}
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI

tools = [{
    "type": "function",
    "function": {
        "name": "watch_video_clip",
        "description": "Watch a video file or a sub-clip of it. If start_time and end_time are not provided, the entire video will be returned.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "The path to the video file to watch"
                },
                "start_time": {
                    "type": "number",
                    "description": "The start time of the clip in seconds (optional, defaults to 0)"
                },
                "end_time": {
                    "type": "number",
                    "description": "The end time of the clip in seconds (optional, defaults to end of video)"
                }
            },
            "required": ["path"]
        }
    }
}]

def watch_video_clip(path: str, start_time: float | None = None, end_time: float | None = None) -> list[dict]:
    """
    Watch a video file or a sub-clip of it.

    Args:
        path: The path to the video file to watch
        start_time: The start time in seconds (optional, defaults to 0)
        end_time: The end time in seconds (optional, defaults to end of video)

    Returns:
        A list of content blocks in MultiModal Tool API format
    """

    video_path = Path(path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    # Get video duration if needed
    if start_time is None and end_time is None:
        # Return entire video
```

...

```python theme={null}
        {"role": "system", "content": "You are a video analysis assistant. Use watch_video_clip to examine specific portions of videos."},
        {"role": "user", "content": user_message}
    ]

    while True:
        response = client.chat.completions.create(
            model="kimi-k2.6",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        message = response.choices[0].message
        messages.append(message.model_dump())

        # No tool calls = done
        if not message.tool_calls:
            return message.content

        # Execute tool calls
        for tool_call in message.tool_calls:
            if tool_call.function.name == "watch_video_clip":
                args = json.loads(tool_call.function.arguments)
                result = watch_video_clip(
                    path=args["path"],
                    start_time=args.get("start_time"),
```

...

## Best Practices
### Supported Formats
Images are supported in formats: png, jpeg, webp, gif.
Videos are supported in formats: mp4, mpeg, mov, avi, x-flv, mpg, webm, wmv, 3gpp.

### Token Calculation and Billing
Image and video token usage is dynamically calculated. You can use the [token estimation API](/docs/api/estimate) to check the expected token consumption for a request containing images or video before processing.

...

### Upload File or Base64?
Due to the limitation on the overall size of the request body, for very large videos you **must** use the file upload method to utilize vision capabilities.For images or videos that will be referenced multiple times, it is recommended to use the file upload method. Regarding file upload limitations, please refer to the [File Upload documentation](/docs/api/files-upload).

...

## Parameters Differences in Request Body
Parameters are listed in [chat](/docs/api/chat). However, behaviour of some parameters may be different in k2.6 models.
**We recommend using the default values instead of manually configuring these parameters.**
Differences are listed below.
| Field | Required | Description | Type | Values |
| max_tokens | optional | The maximum number of tokens to generate for the chat completion. | int | Default to be 32k aka 32768 |
| thinking | optional | **New!** This parameter controls if the thinking is enabled for this request | object | Default to be `{"type": "enabled"}`. Value can only be one of `{"type": "enabled"}` or `{"type": "disabled"}` |
| temperature | optional | The sampling temperature to use | float | k2.6 model will use a fixed value 1.0, non-thinking mode will use a fixed value 0.6. Any other value will result in an error |
| top_p | optional | A sampling method | float | k2.6 model will use a fixed value 0.95. Any other value will result in an error |
| n | optional | The number of results to generate for each input message | int | k2.6 model will use a fixed value 1. Any other value will result in an error |

...

## Tool Use Compatibility
* `tool_choice` can only be set to "auto" or "none" (default is "auto") to avoid conflicts between reasoning content and the specified tool_choice. Any other value will result in an error;
* During multi-step tool calling, we recommend keeping the `reasoning_content` from the assistant message in the current turn's tool call within the context; omitting it does not cause an error, but may degrade reasoning continuity and tool-call quality;
* The official builtin `$web_search` tool is temporarily incompatible with Kimi K2.6 thinking mode, you can choose to disable thinking mode first and then use the `$web_search` tool.
You can refer to [Use Thinking Mode](/docs/guide/use-thinking-models) for correct usage of tool calling.

### Disable Thinking Capability Example
For the `kimi-k2.6` model, you can disable thinking by specifying `"thinking": {"type": "disabled"}` in the request body:
<Tabs>
<Tab title="curl">
`bash theme={null}     $ curl https://api.moonshot.ai/v1/chat/completions \         -H "Content-Type: application/json" \         -H "Authorization: Bearer $MOONSHOT_API_KEY" \         -d '{             "model": "kimi-k2.6",             "messages": [                 {"role": "user", "content": "hello"}             ],             "thinking": {"type": "disabled"}        }'     `
</Tab>