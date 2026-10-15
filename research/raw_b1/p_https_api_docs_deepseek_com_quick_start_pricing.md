# https://api-docs.deepseek.com/quick_start/pricing
# extracted 2026-10-15T10:56:29.826299Z

# Your First API Call
The DeepSeek API uses an API format compatible with OpenAI/Anthropic. By modifying the configuration, you can use the OpenAI/Anthropic SDK or softwares compatible with the OpenAI/Anthropic API to access the DeepSeek API.

...

(1) Use `deepseek-flash` as the model name. The legacy names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price.

...

## Integrate with Agent Tools ​
The DeepSeek API is supported by many popular AI agent and coding assistant tools. If you use tools like Claude Code, GitHub Copilot, or OpenCode, you can use DeepSeek as the backend model directly — no code required.

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
* [Email](mailto:api-service@deepseek.com)
* [Discord](https://discord.gg/Tc7c45Zzu5)
* [Twitter](https://twitter.com/deepseek_ai)
More
* [GitHub](https://github.com/deepseek-ai)