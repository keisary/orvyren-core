# https://platform.moonshot.ai/docs/pricing/chat
# extracted 2026-10-15T10:56:29.827304Z

# Model Inference Pricing Explanation
## ​
Concepts
Model inference on the Kimi API platform is billed on a pay-as-you-go basis, with no subscription plan. It differs from products such as the Kimi membership and Kimi Code. [See the product comparison](https://platform.moonshot.ai/docs/guide/product-plans) .

...

### ​
Model inference APIs bill both Input and Output based on usage. For K3 series models, cache writes are billed separately by TTL (5min / 1h); cached input is billed at the cache-hit price only, with no additional cache write charge. If you upload and extract content from a document and then pass the extracted content as Input to the model, the document content will also be billed based on usage.
File-related APIs (file content extraction and file storage) are **temporarily free** : if you only upload and extract a document, the file APIs themselves incur no charges.