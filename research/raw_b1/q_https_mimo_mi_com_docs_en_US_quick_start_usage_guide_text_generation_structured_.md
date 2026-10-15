# https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/structured-output
# extracted 2026-10-15T10:57:10.116758Z

Quick Start Usage Guide Text Generation Structured Output
Ctrl
Overview
[Welcome](https://mimo.mi.com/docs/en-US/quick-start/summary/welcome)
[First API Call](https://mimo.mi.com/docs/en-US/quick-start/summary/first-api-call)
[Models](https://mimo.mi.com/docs/en-US/quick-start/summary/model)
Usage Guide
Text Generation
Tool Calling
[Web Search](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/tool-calling/web-search)
[Deep Thinking](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/deep-thinking)
[Structured Output](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/structured-output)
[Batch Inference (Batch API)](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/batch-api)
Multimodal Understanding
[Image Understanding](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/multimodal-understanding/image-understanding)
[Audio Understanding](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/multimodal-understanding/audio-understanding)
[Video Understanding](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/multimodal-understanding/video-understanding)
Audio
[Speech Recognition（MiMo-V2.5-ASR）](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/audio/Speech-Recognition)

...

[Team Edition Benefits Related](https://mimo.mi.com/docs/en-US/quick-start/faq/token-plan/Team-Benefits)
[Token Plan and Desktop Membership](https://mimo.mi.com/docs/en-US/quick-start/faq/token-plan/desktop-guide)
[Promotions](https://mimo.mi.com/docs/en-US/quick-start/faq/promotions)
[Others](https://mimo.mi.com/docs/en-US/quick-start/faq/others)
Terms & Agreements
[Service Agreement](https://mimo.mi.com/docs/quick-start/terms/user-agreement)
[Privacy Policy](https://mimo.mi.com/docs/quick-start/terms/privacy-policy)
[Transparency](https://mimo.mi.com/docs/quick-start/terms/transparency)
Invite friends

...

# Structured Outputs
## Call Examples
### Basic Call
```
 client  =  OpenAI (     api_key = os . environ . get ( "MIMO_API_KEY" ) ,     base_url = "https://api.xiaomimimo.com/v1" ) completion  =  client . chat . completions . create (     model = "mimo-v2.6-pro" ,     messages = [ { "role" : "system" , "content" : "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nDo not add any explanations outside JSON. Parse meeting information and return nested structured JSON: {\"meeting_meta\": {\"meeting_topic\": string | null, \"start_time\": string | null, \"participants\": array<string>}, \"action_items\": [{\"task\": string, \"responsible_person\": string, \"deadline\": string}]}\nFill null for unknown fields." } , { "role" : "user" , "content" : "Product iteration meeting at 14:00 tomorrow. Attendees: Li Ming, Wang Hua. Task: Complete API document revision by Friday, taken by Wang Hua." } ] ,     response_format = { "type" : "json
```

...

```
{ "id" : "d7bbc231-ed6a-4884-a9e4-d7caff96cf25_c37a9ce97e9542079b9d948b07c10209" , "choices" : [ { "finish_reason" : "stop" , "index" : 0 , "message" : { "content" : "{\"meeting_meta\": {\"meeting_topic\": \"Product iteration meeting\", \"start_time\": \"2025-12-17 14:00\", \"participants\": [\"Li Ming\", \"Wang Hua\"]}, \"action_items\": [{\"task\": \"Complete API document revision\", \"responsible_person\": \"Wang Hua\", \"deadline\": \"2025-12-19\"}]}" , "role" : "assistant" , "tool_calls" : null , "reasoning_content" : "The user wants me to parse meeting information and return structured JSON.\n\nMeeting: Product iteration meeting\nTime: 14:00 tomorrow\nParticipants: Li Ming, Wang Hua\nTask: Complete API document revision by Friday, responsible: Wang Hua\n\nI need to fill unknown fields with null. Today's date is Tuesday, December 16, 2025, so tomorrow is December 17, 2025. But I should probably just put what was given: \"14:00 tomorrow\" — I could inter
```

...

### Streaming Output
```
 client  =  OpenAI (     api_key = os . environ . get ( "MIMO_API_KEY" ) ,     base_url = "https://api.xiaomimimo.com/v1" ) completion  =  client . chat . completions . create (     model = "mimo-v2.6-pro" ,     messages = [ { "role" : "system" , "content" : "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\nReturn only compact JSON without any extra explanations. Use the specified format: {\"destination\": string, \"trip_days\": number, \"core_activity\": array<string>, \"budget_level\": \"low\"|\"mid\"|\"high\"}" } , { "role" : "user" , "content" : "Plan a 3-day city trip focusing on museums and local food with a moderate budget." } ] ,     response_format = { "type" : "json_object" } ,     stream = True ) full_json_content  = "" for  chunk  in  completion : if not  chunk . choices : continue     message_delta  =  chunk . choices [ 0 ] . delta
```

...

## How to Get Accurate JSON Output
```
 client  =  OpenAI (     api_key = os . environ . get ( "MIMO_API_KEY" ) ,     base_url = "https://api.xiaomimimo.com/v1" ) ticket_schema  = { "type" : "object" , "properties" : { "problem_type" : { "type" : "string" , "enum" : [ "device_fault" , "consult" , "complaint" , "other" ] } , "device_model" : { "type" : [ "string" , "null" ] } , "urgent_level" : { "type" : "string" , "enum" : [ "low" , "normal" , "high" ] } , "user_requirements" : { "type" : "array" , "items" : { "type" : "string" } } } , "required" : [ "problem_type" , "device_model" , "urgent_level" , "user_requirements" ] } def extract_ticket ( text : str ) :     sys_prompt  = ( "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.\n" "Return JSON only, no explanations, no extra text.\n" "Format: {\"problem_type\":\"device_fault|consult|complaint|other\",\"device_model\":string|null,\"urgen
```

...

Update Time September 21, 2026
[Deep Thinking](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/deep-thinking) [Batch Inference (Batch API)](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/batch-api)

### Table of Contents
Supported Models
Request Parameters
Call Examples
Basic Call
Streaming Output
How to Get Accurate JSON Output
Scroll to top
[](https://mimo.mi.com/ "MiMo")
[](mailto:support-mimo@xiaomi.com)
WeChat QR Official Account

...

#### Products
[Xiaomi MiMo API](https://mimo.mi.com/docs/quick-start/summary/model) [Xiaomi MiMo Desktop](https://mimo-ai.xiaomimimo.com/desktop/invite/) [Xiaomi MiMo Claw](https://aistudio.xiaomimimo.com/open-apis/v1/genLoginUrl?currentPath=/?forcePage=claw) [Xiaomi MiMo Studio](https://aistudio.xiaomimimo.com/open-apis/v1/genLoginUrl?currentPath=/?forcePage=chat) [Xiaomi MiMo Code](https://mimo.xiaomi.com/mimocode)

#### Open Platform
[Docs](https://mimo.mi.com/docs/welcome) [FAQ](https://mimo.mi.com/docs/quick-start/faq/) [API Pricing](https://mimo.mi.com/docs/price/pay-as-you-go) [Token Plan](https://platform.xiaomimimo.com/token-plan)