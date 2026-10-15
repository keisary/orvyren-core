# Rate Limit

{/* feishu-style:text-align:left */}
This page lists all the models currently supported by the Xiaomi MiMo API Open Platform and their rate-limiting quotas, helping you plan your request frequency before integration. 

### Rate Limiting Instructions

{/* feishu-style:text-align:left */}
The platform sets a model concurrency limit for each account. When the server load is high, response delays or ` 429 ` error may occur. We recommend that you plan your request frequency reasonably and implement request retry and backoff strategies in high-concurrency scenarios to avoid triggering rate limits. 

<div className='mdx-highlight mdx-highlight-info' data-highlight-icon='info'>

- **RPM (Requests Per Minute)** : The maximum number of requests initiated per minute. The calculation scope is the sum of the total number of requests from all API Keys under a single account when calling the same model.

- **TPM (Tokens Per Minute)** : The maximum number of Tokens that can be interacted with per minute. The calculation scope is the sum of the total number of requested Tokens for all API Keys under a single account when calling the same model.

</div>

### Text Generation Model

<table>
<colgroup>
<col style="width: 44.04%" />
<col style="width: 27.98%" />
<col style="width: 27.980000000000004%" />
</colgroup>
<thead>
<tr>
<th><span style="display: inline-block; width: 100%; text-align: left;">Model ID</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">RPM</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">TPM</span></th>
</tr>
</thead>
<tbody>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.6-pro`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.6-flash`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.6-pro-ultraspeed`</span></td>
<td colspan="2"><span style="display: inline-block; width: 100%; text-align: left;">Customized services available, please [contact us](https://platform.xiaomimimo.com/contact?userId=2451887661)</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5-pro`(to be deprecated)</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5`(to be deprecated)</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
</tbody>
</table>

### Automatic Speech Recognition Model (ASR) 

<table>
<colgroup>
<col style="width: 44.04%" />
<col style="width: 27.98%" />
<col style="width: 27.980000000000004%" />
</colgroup>
<thead>
<tr>
<th><span style="display: inline-block; width: 100%; text-align: left;">Model ID</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">RPM</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">TPM</span></th>
</tr>
</thead>
<tbody>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5-asr`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10K</span></td>
</tr>
</tbody>
</table>

### Text-to-Speech (TTS) Model

<table>
<colgroup>
<col style="width: 44.04%" />
<col style="width: 27.98%" />
<col style="width: 27.980000000000004%" />
</colgroup>
<thead>
<tr>
<th><span style="display: inline-block; width: 100%; text-align: left;">Model ID</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">RPM</span></th>
<th><span style="display: inline-block; width: 100%; text-align: left;">TPM</span></th>
</tr>
</thead>
<tbody>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5-tts`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5-tts-voiceclone`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
<tr>
<td><span style="display: inline-block; width: 100%; text-align: left;">`mimo-v2.5-tts-voicedesign`</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">100</span></td>
<td><span style="display: inline-block; width: 100%; text-align: left;">10M</span></td>
</tr>
</tbody>
</table>
