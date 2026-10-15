# https://api-docs.deepseek.com/guides/json_mode
# extracted 2026-10-15T10:54:07.139853Z

* [](https://api-docs.deepseek.com/)
* JSON Output
On this page

# JSON Output
In many scenarios, users need the model to output in strict JSON format to achieve structured output, facilitating subsequent parsing.
DeepSeek provides JSON Output to ensure the model outputs valid JSON strings.

...

## Notice ​
1. Set the `response_format` parameter to `{'type': 'json_object'}` .
2. Include the word "json" in the system or user prompt, and provide an example of the desired JSON format to guide the model in outputting valid JSON.
3. Set the `max_tokens` parameter reasonably to prevent the JSON string from being truncated midway.
4. **When using the JSON Output feature, the API may occasionally return empty content. We are actively working on optimizing this issue.

...

## Sample Code ​
```
import  json  
 from  openai  import  OpenAI  
   
 client  =  OpenAI (  
     api_key = "<your api key>" ,  
     base_url = "https://api.deepseek.com" ,  
 )  
   
 system_prompt  = """  
 The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format.   
   
 EXAMPLE INPUT:   
 Which is the highest mountain in the world? Mount Everest.  
   
 EXAMPLE JSON OUTPUT:  
 {  
     "question": "Which is the highest mountain in the world?",  
     "answer": "Mount Everest"  
 }  
 """  
   
 user_prompt  = "Which is the longest river in the world? The Nile River."  
   
 messages  = [ { "role" : "system" , "content" :  system_prompt } ,  
 { "role" : "user" , "content" :  user_prompt } ]  
   
 response  =  client . chat . completions . create (  
     model = "deepseek-flash" ,  
     messages = messages ,  
     response_format = {  
 'type' : 'json_object'  
 }  
 )  
   
```