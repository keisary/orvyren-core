# Structured Outputs

{/* feishu-style:text-align:left */}
Structured Output (JSON mode) enables models to generate responses in a specified JSON format, ensuring outputs are controllable and easy to parse. It is suitable for scenarios requiring structured data, such as data extraction, form filling, classification and tagging, and API response formatting.

## Supported Models

{/* feishu-style:text-align:left */}
Currently, the `mimo-v2.6-flash`, `mimo-v2.6-pro`, `mimo-v2.6-pro-ultraspeed`, `mimo-v2.5-pro` and `mimo-v2.5` models are supported.

## Request Parameters

- `response_format`: Response format control parameter. Pass `{"type": "json_object"}` to enable JSON mode output.

- `messages`: You must explicitly instruct the model in the system or user message to return only JSON, and fully define the fields, hierarchy, and data types of the expected JSON structure. Providing examples is recommended.

<div className='mdx-highlight mdx-highlight-warning' data-highlight-icon='warning'>

Plan the value of `max_completion_tokens` carefully. Setting it too low may cause the output to be truncated, resulting in incomplete JSON that cannot be parsed.

</div>

## Call Examples

### Basic Call

<Tab>
  <TabItem label={`Python SDK`}>

```python
import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.6-pro",
    messages=[
        {
            "role": "system",
            "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nDo not add any explanations outside JSON. Parse meeting information and return nested structured JSON: {\"meeting_meta\": {\"meeting_topic\": string | null, \"start_time\": string | null, \"participants\": array<string>}, \"action_items\": [{\"task\": string, \"responsible_person\": string, \"deadline\": string}]}\nFill null for unknown fields."
        },
        {
            "role": "user",
            "content": "Product iteration meeting at 14:00 tomorrow. Attendees: Li Ming, Wang Hua. Task: Complete API document revision by Friday, taken by Wang Hua."
        }
    ],
    response_format={
        "type": "json_object"
    }
)

result = completion.choices[0].message.content
try:
    parsed_json_data = json.loads(result)
    print(json.dumps(parsed_json_data, indent=4, ensure_ascii=False))
except json.JSONDecodeError as e:
    print(f"JSON parsing failed: {str(e)}")
    print(f"Raw complete content: {result}")
```

  </TabItem>
  <TabItem label={`Curl`}>

```bash
curl --location --request POST 'https://api.xiaomimimo.com/v1/chat/completions' \
--header "api-key: $MIMO_API_KEY" \
--header "Content-Type: application/json" \
--data-raw '{
    "model": "mimo-v2.6-pro",
    "messages": [
        {
            "role": "system",
            "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nDo not add any explanations outside JSON. Parse meeting information and return nested structured JSON: {\"meeting_meta\": {\"meeting_topic\": string | null, \"start_time\": string | null, \"participants\": array<string>}, \"action_items\": [{\"task\": string, \"responsible_person\": string, \"deadline\": string}]}\nFill null for unknown fields."
        },
        {
            "role": "user",
            "content": "Product iteration meeting at 14:00 tomorrow. Attendees: Li Ming, Wang Hua. Task: Complete API document revision by Friday, taken by Wang Hua."
        }
    ],
    "response_format": {
        "type": "json_object"
    }
}'
```

  </TabItem>
</Tab>

{/* feishu-style:text-align:left */}
**Response Example**

```json
{
    "id": "d7bbc231-ed6a-4884-a9e4-d7caff96cf25_c37a9ce97e9542079b9d948b07c10209",
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "{\"meeting_meta\": {\"meeting_topic\": \"Product iteration meeting\", \"start_time\": \"2025-12-17 14:00\", \"participants\": [\"Li Ming\", \"Wang Hua\"]}, \"action_items\": [{\"task\": \"Complete API document revision\", \"responsible_person\": \"Wang Hua\", \"deadline\": \"2025-12-19\"}]}",
                "role": "assistant",
                "tool_calls": null,
                "reasoning_content": "The user wants me to parse meeting information and return structured JSON.\n\nMeeting: Product iteration meeting\nTime: 14:00 tomorrow\nParticipants: Li Ming, Wang Hua\nTask: Complete API document revision by Friday, responsible: Wang Hua\n\nI need to fill unknown fields with null. Today's date is Tuesday, December 16, 2025, so tomorrow is December 17, 2025. But I should probably just put what was given: \"14:00 tomorrow\" — I could interpret it. The instruction says to fill null for unknown fields. \"Tomorrow\" relative to today (2025-12-16) is 2025-12-17. I'll provide \"2025-12-17 14:00\" as start_time. Actually, the user message just says \"at 14:00 tomorrow\" — it's reasonable to resolve it. Friday relative to 2025-12-17 would be 2025-12-19. I'll provide that.\n\nI'll return JSON only, no explanations outside JSON."
            }
        }
    ],
    "created": 1790008400,
    "model": "mimo-v2.6-pro",
    "object": "chat.completion",
    "usage": {
        "completion_tokens": 344,
        "prompt_tokens": 161,
        "total_tokens": 505,
        "completion_tokens_details": {
            "reasoning_tokens": 253
        },
        "prompt_tokens_details": {
            "cached_tokens": 0
        }
    }
}
```

### Streaming Output

<Tab>
  <TabItem label={`Python SDK`}>

> In streaming mode, the model outputs JSON content incrementally. You must concatenate the complete JSON string on the client side before parsing to avoid failures caused by truncation.

```python
import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.6-pro",
    messages=[
        {
            "role": "system",
            "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nReturn only compact JSON without any extra explanations. Use the specified format: {\"destination\": string, \"trip_days\": number, \"core_activity\": array<string>, \"budget_level\": \"low\"|\"mid\"|\"high\"}"
        },
        {
            "role": "user",
            "content": "Plan a 3-day city trip focusing on museums and local food with a moderate budget."
        }
    ],
    response_format={
        "type": "json_object"
    },
    stream=True
)

full_json_content = ""
for chunk in completion:
    if not chunk.choices:
        continue
    message_delta = chunk.choices[0].delta
    if message_delta.content:
        full_json_content += message_delta.content

try:
    parsed_json_data = json.loads(full_json_content)
    print(json.dumps(parsed_json_data, indent=4, ensure_ascii=False))
except json.JSONDecodeError as e:
    print(f"JSON parsing failed: {str(e)}")
    print(f"Raw complete content: {full_json_content}")

```

  </TabItem>
  <TabItem label={`Curl`}>

```bash
curl --location --request POST 'https://api.xiaomimimo.com/v1/chat/completions' \
--header "api-key: $MIMO_API_KEY" \
--header "Content-Type: application/json" \
--data-raw '{
    "model": "mimo-v2.6-pro",
    "messages": [
        {
            "role": "system",
            "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nReturn only compact JSON without any extra explanations. Use the specified format: {\"destination\": string, \"trip_days\": number, \"core_activity\": array<string>, \"budget_level\": \"low\"|\"mid\"|\"high\"}"
        },
        {
            "role": "user",
            "content": "Plan a 3-day city trip focusing on museums and local food with a moderate budget."
        }
    ],
    "response_format": {
        "type": "json_object"
    },
    "stream": true
}'

```

  </TabItem>
</Tab>

{/* feishu-style:text-align:left */}
**Response Example (Concatenated Streaming Result)** 

```json
{
    "destination": "Lisbon, Portugal",
    "trip_days": 3,
    "core_activity": [
        "Visit the National Museum of Ancient Art",
        "Explore the MAAT and Belém cultural district",
        "Wander the Calouste Gulbenkian Museum",
        "Taste pastéis de nata at Pastéis de Belém",
        "Sample petiscos and seafood at Time Out Market",
        "Try bacalhau and bifana in local tascas",
        "Walk through Alfama with fado dinner"
    ],
    "budget_level": "mid"
}
```

## How to Get Accurate JSON Output

{/* feishu-style:text-align:left */}
The `json_object` mode only guarantees syntactically valid JSON output. The actual data structure is entirely defined by your prompt. The clearer and more complete your prompt constraints are, the more closely the model's JSON output will match your expectations.

{/* feishu-style:text-align:left */}
**1. Enforce JSON-Only Output**

{/* feishu-style:text-align:left */}
Explicitly require the model to return JSON only, with no explanations, comments, or Markdown code blocks, to prevent parsing errors caused by extra text.

{/* feishu-style:text-align:left */}
**2. Provide a Complete JSON Structure Template**

{/* feishu-style:text-align:left */}
List all fields, data types, and nesting levels completely. Adding examples makes it easier to constrain the model:

```json
{
  "name": string,
  "count": number,
  "tags": string[],
  "date": "YYYY-MM-DD"
}
```

{/* feishu-style:text-align:left */}
**3. Constrain Enum Values and Numeric Ranges**

- Use enum annotations for fixed options: `"status": "active" | "inactive" | "pending"`

- Constrain numeric ranges: `score: number (0-100)`

{/* feishu-style:text-align:left */}
**4. Define Null Value Handling Rules**

{/* feishu-style:text-align:left */}
Specify in advance that unknown fields should be filled with `null`, e.g., in your prompt: fill null for unknown fields.

{/* feishu-style:text-align:left */}
**5. Ensure Reliable JSON Output**

{/* feishu-style:text-align:left */}
Enabling `json_object` mode only guarantees syntactically valid JSON; it cannot enforce that returned fields, data types, and nesting match your predefined structure. In production environments, it is recommended to use the `jsonschema` library for strict structural validation of model output. If validation fails, you can retry with an enhanced prompt, apply business-level fallback logic, or take other contingency measures.

{/* feishu-style:text-align:left */}
Below is a Python example. The scenario: parse customer service conversation text, automatically extract core ticket information, and implement automatic ticket classification, urgency level assignment, and intelligent dispatch.

```python
import json
import os
from jsonschema import validate, ValidationError
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

ticket_schema = {
    "type": "object",
    "properties": {
        "problem_type": {
            "type": "string",
            "enum": ["device_fault", "consult", "complaint", "other"]
        },
        "device_model": {"type": ["string", "null"]},
        "urgent_level": {
            "type": "string",
            "enum": ["low", "normal", "high"]
        },
        "user_requirements": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["problem_type", "device_model", "urgent_level", "user_requirements"]
}

def extract_ticket(text: str):
    sys_prompt = (
        "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\n"
        "Return JSON only, no explanations, no extra text.\n"
        "Format: {\"problem_type\":\"device_fault|consult|complaint|other\",\"device_model\":string|null,\"urgent_level\":\"low|normal|high\",\"user_requirements\":array<string>}\n"
        "Fill null if device model is unknown."
    )
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": text}
    ]

    resp = client.chat.completions.create(
        model="mimo-v2.6-pro",
        messages=messages,
        response_format={"type": "json_object"},
        stream=False
    )
    json_text = resp.choices[0].message.content
    data = json.loads(json_text)

    try:
        validate(instance=data, schema=ticket_schema)
        return {"ok": True, "data": data}
    except ValidationError as e:
        return {"ok": False, "error": e.message, "raw": data}

if __name__ == "__main__":
    # Test with two sample tickets
    input_list = [
        "My speaker can't connect Wi-Fi, I restarted it but no use, hope to solve quickly, don't know the model.",
        "Want to ask how to set timing function, device model is Watch S1, no urgent demand."
    ]

    for idx, text in enumerate(input_list, 1):
        print(f"==== Ticket {idx} extraction result ====")
        res = extract_ticket(text)
        if res["ok"]:
            print(json.dumps(res["data"], indent=4))
        else:
            print(f"Validation failed: {res['error']}")

```
