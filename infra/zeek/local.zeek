@load policy/tuning/json-logs.zeek

# Docker/VM: locally-generated packets have unfilled checksums (offload).
# Without this Zeek silently drops them.
redef ignore_checksums = T;