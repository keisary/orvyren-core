# https://api-docs.deepseek.com/guides/function_calling
# extracted 2026-10-15T10:57:10.113752Z

* [](https://api-docs.deepseek.com/)
* Your First API Call
On this page

# Your First API Call
The DeepSeek API uses an API format compatible with OpenAI/Anthropic. By modifying the configuration, you can use the OpenAI/Anthropic SDK or softwares compatible with the OpenAI/Anthropic API to access the DeepSeek API.
| PARAM | VALUE |
| base_url (OpenAI) | `https://api.deepseek.com` |
| base_url (Anthropic) | `https://api.deepseek.com/anthropic` |
| api_key | apply for an [API key](https://platform.deepseek.com/api_keys) |
| model | `deepseek-flash` (1) |
| `deepseek-v4-pro` |  |
(1) Use `deepseek-flash` as the model name. The legacy names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price.

## Integrate with Agent Tools ​
DeepSeek Harness is now in developer preview for agent harness developers worldwide. See the [DeepSeek Harness Guide](https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart) for details.

...

See the [Agent Integrations Guide](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code) for details.

## Invoke The Chat API ​
Once you have obtained an API key, you can access the DeepSeek model using the following example scripts in the OpenAI API format. This is a non-stream example, you can set the `stream` parameter to `true` to get stream response.
For examples using the Anthropic API format, please refer to [Anthropic API](https://api-docs.deepseek.com/guides/anthropic_api) .
* curl
* python
* nodejs
```
curl https://api.deepseek.com/chat/completions \  
   -H "Content-Type: application/json" \  
   -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \  
   -d '{  
         "model": "deepseek-flash",  
         "messages": [  
           {"role": "system", "content": "You are a helpful assistant."},  
           {"role": "user", "content": "Hello!"}  
         ],  
         "thinking": {"type": "enabled"},  
         "reasoning_effort": "high",  
         "stream": false  
       }'
```