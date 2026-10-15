# https://mimo.mi.com/docs/en-US/api/model/list-models
# extracted 2026-10-15T10:57:10.115758Z

[](https://mimo.mi.com/ "Back to Home")
Documentation
[Research](https://mimo.xiaomi.com/)
Models
Updates
Pricing
[Contact Us](https://platform.xiaomimimo.com/contact)
English
[Console](https://platform.xiaomimimo.com/console/balance)
[](https://mimo.mi.com/ "Back to Home")
Documentation
API Reference Models List Models
Ctrl
API Guidance
[Rate Limit](https://mimo.mi.com/docs/en-US/api/guidance/rate-limit)
[Model Hyperparameters](https://mimo.mi.com/docs/en-US/api/guidance/model-hyperparameters)
[Error Codes](https://mimo.mi.com/docs/en-US/api/guidance/error-codes)
Chat
[POST OpenAI Chat Completion API](https://mimo.mi.com/docs/en-US/api/chat/openai-api)
[POST OpenAI Responses API](https://mimo.mi.com/docs/en-US/api/chat/responses)
[POST Anthropic API](https://mimo.mi.com/docs/en-US/api/chat/anthropic-api)
Audio
[POST Speech Recognition (MiMo‑V2.5-ASR) - OpenAI API Compatibility](https://mimo.mi.com/docs/en-US/api/audio/Speech-Recognition)
[POST Speech Synthesis (MiMo-TTS Series) - OpenAI API Compatibility](https://mimo.mi.com/docs/en-US/api/audio/tts)
Models
[GET List Models](https://mimo.mi.com/docs/en-US/api/model/list-models)
Invite friends

# List Models
## Request Address
```
https://api.xiaomimimo.com/v1/models
```

## Request Headers
The API supports the following two authentication methods. Please choose one and add it to the request headers:
API Key Authentication Bearer Authentication
```
api-key :  $MIMO_API_KEY
```

## Response
* object string
  The object type.
  Available options: `list`
* data array
  An array of model objects.
  Hide child attributes
  data. id string
  The model identifier, which can be referenced in the API endpoints.
  data. object string
  The object type.
  Available options: `model`
  data. owned_by string
  The organization that owns the model.
curl python
list models
```
curl --location --request GET 'https://api.xiaomimimo.com/v1/models' \ 
 --header "api-key:  $MIMO_API_KEY "
```
response
list models
```
{ 
    "object" : "list" , 
    "data" : [ 
        { 
            "id" : "mimo-v2.5" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-asr" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-pro" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts-voiceclone" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts-voicedesign" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.6-flash" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
```

...

Update TimeJuly 17, 2026
[Speech Synthesis (MiMo-TTS Series) - OpenAI API Compatibility](https://mimo.mi.com/docs/en-US/api/audio/tts) [Pay‑As‑You‑Go API](https://mimo.mi.com/docs/en-US/price/pay-as-you-go)
Table of Contents
curl python
list models
```
curl --location --request GET 'https://api.xiaomimimo.com/v1/models' \ 
 --header "api-key:  $MIMO_API_KEY "
```
response
list models
```
{ 
    "object" : "list" , 
    "data" : [ 
        { 
            "id" : "mimo-v2.5" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-asr" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-pro" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts-voiceclone" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.5-tts-voicedesign" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
        } , 
        { 
            "id" : "mimo-v2.6-flash" , 
            "object" : "model" , 
            "owned_by" : "xiaomi" 
```

...

### About Us
* MiMo-V2.6-Pro : Our most powerful flagship reasoning model to date — omni-modal, ultra-high performance, trillion-parameter — built for complex projects, long-horizon tasks, high-stakes work, cybersecurity, and research.
* MiMo-V2.6-Flash : Full-modality, high-intelligence, low-cost reasoning model — the best balance for high-frequency calls and large-scale tasks in professional workflows.
* MiMo-V2.6-Pro-Ultraspeed : Flagship V2.6-Pro performance, output up to 20x faster.

...

Full modality across the series, optimized for professional scenarios — pareto-optimal choice balancing performance, speed, and cost.
Xiaomi MiMo Batch API Now Available