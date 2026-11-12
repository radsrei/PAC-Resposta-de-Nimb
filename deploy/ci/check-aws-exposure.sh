#!/usr/bin/env bash
# CI-08 (produção): depois do deploy, confere a exposição da EC2 na AWS.
# Roda no runner do GitHub com as credenciais do CD (aws cli configurado).
#
#   EC2_INSTANCE_ID=i-... EXPECTED_OPEN_PORTS="" bash deploy/ci/check-aws-exposure.sh
#
# EXPECTED_OPEN_PORTS: portas que PODEM responder no IP público, separadas por espaço.
#   Modo Cloudflare Tunnel (recomendado): vazio — nada responde, nem 80/443.
#   Modo B (HTTPS pelo próprio Caddy):    "80 443".
set -euo pipefail
: "${EC2_INSTANCE_ID:?defina EC2_INSTANCE_ID}"
EXPECTED_OPEN_PORTS="${EXPECTED_OPEN_PORTS:-}"
PROBE_PORTS="22 80 443 3000 8000 11434"

fail=0
ok()  { echo "  ok    $*"; }
bad() { echo "  FALHA $*"; fail=1; }

echo "==> Security groups de $EC2_INSTANCE_ID"
read -r PUBLIC_IP SG_IDS < <(aws ec2 describe-instances --instance-ids "$EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].[PublicIpAddress, join(`,`, SecurityGroups[].GroupId)]' --output text)
echo "  IP público: $PUBLIC_IP   SGs: $SG_IDS"

# Regras de entrada abertas para a internet inteira (0.0.0.0/0 ou ::/0)
open_rules="$(aws ec2 describe-security-groups --group-ids ${SG_IDS//,/ } --output json \
  | jq -r '.SecurityGroups[] | .GroupId as $g | .IpPermissions[]
           | select(any(.IpRanges[]?; .CidrIp=="0.0.0.0/0") or any(.Ipv6Ranges[]?; .CidrIpv6=="::/0"))
           | "\($g) \(.IpProtocol) \(.FromPort // "all")-\(.ToPort // "all")"')"
allowed_world=""
for p in $EXPECTED_OPEN_PORTS; do allowed_world="$allowed_world tcp $p-$p"; done
if [ -z "$open_rules" ]; then
  ok "nenhuma regra aberta para 0.0.0.0/0 ou ::/0"
else
  while read -r g proto range; do
    if [[ " $allowed_world " == *" $proto $range "* ]]; then ok "$g $proto $range (permitida)"; else bad "$g $proto $range aberta para a internet"; fi
  done <<< "$open_rules"
fi

if [ "$PUBLIC_IP" = "None" ] || [ -z "$PUBLIC_IP" ]; then
  ok "instância sem IP público"; exit $fail
fi

echo "==> Varredura de portas no IP público (a partir do runner)"
for port in $PROBE_PORTS; do
  if timeout 4 bash -c "</dev/tcp/$PUBLIC_IP/$port" 2>/dev/null; then
    if [[ " $EXPECTED_OPEN_PORTS " == *" $port "* ]]; then ok "$port aberta (esperado)"; else bad "$port responde no IP público"; fi
  else
    if [[ " $EXPECTED_OPEN_PORTS " == *" $port "* ]]; then bad "$port deveria responder"; else ok "$port fechada"; fi
  fi
done

exit $fail
