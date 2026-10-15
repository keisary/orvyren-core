#!/bin/bash
# usage: rpc_check.sh <rpc_url> <label> <addr1> [addr2 ...]
rpc="$1"; label="$2"; shift 2
echo "=== $label"
curl -s -m 25 "$rpc" -H 'content-type: application/json' -H 'user-agent: curl/8' -d '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' | head -c 200; echo
bn=$(curl -s -m 25 "$rpc" -H 'content-type: application/json' -H 'user-agent: curl/8' -d '{"jsonrpc":"2.0","id":2,"method":"eth_blockNumber","params":[]}')
echo "blockNumber: $bn"
for a in "$@"; do
  r=$(curl -s -m 25 "$rpc" -H 'content-type: application/json' -H 'user-agent: curl/8' -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"eth_getCode\",\"params\":[\"$a\",\"latest\"]}")
  code=$(echo "$r" | sed -n 's/.*"result":"\([^"]*\)".*/\1/p')
  if [ -z "$code" ]; then echo "$a -> RPC_ERROR/EMPTY: $(echo $r | head -c 200)"; 
  elif [ "$code" = "0x" ]; then echo "$a -> CODE_ABSENT (0x)";
  else echo "$a -> code_len_bytes=$(( (${#code}-2)/2 )) sha256=$(echo -n "$code" | sha256sum | cut -c1-16)"; fi
done
