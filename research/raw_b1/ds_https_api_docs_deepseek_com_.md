# https://api-docs.deepseek.com/
# extracted 2026-10-15T10:54:07.137847Z

# Your First API Call
The DeepSeek API uses an API format compatible with OpenAI/Anthropic. By modifying the configuration, you can use the OpenAI/Anthropic SDK or softwares compatible with the OpenAI/Anthropic API to access the DeepSeek API.
| PARAM | VALUE |
| base_url (OpenAI) | `https://api.deepseek.com` |
| base_url (Anthropic) | `https://api.deepseek.com/anthropic` |
| api_key | apply for an [API key](https://platform.deepseek.com/api_keys) |
| model | `deepseek-flash` (1) |
| `deepseek-v4-pro` |  |
(1) Use `deepseek-flash` as the model name. The legacy names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price.

...

## Invoke The Chat API ​
Once you have obtained an API key, you can access the DeepSeek model using the following example scripts in the OpenAI API format. This is a non-stream example, you can set the `stream` parameter to `true` to get stream response.

...

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
[Next Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)
* Integrate with Agent Tools
* Invoke The Chat API
WeChat Official Account
* WeChat QRcode
Community