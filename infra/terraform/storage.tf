# ─── STORAGE ──────────────────────────────────────────────────────────────────
# First resource created in this project. Kept as a place to store artefacts
# (reports, exported dashboards) later.
resource "aws_s3_bucket" "artifacts" {
  bucket = "dns-monitor-artifacts"
}