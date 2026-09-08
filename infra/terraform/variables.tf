# ─── VARIABLES ────────────────────────────────────────────────────────────────
# Values supplied from outside the code (environment variables), so nothing
# location-specific or secret is hardcoded into the files themselves.

variable "my_ip" {
  description = "Your current public IP in CIDR form (e.g. 1.2.3.4/32). Set via TF_VAR_my_ip."
  type        = string
}