# ─── NETWORK ──────────────────────────────────────────────────────────────────
# The private network for the deployment — like renting a floor in a building.
# 10.0.0.0/16 gives us ~65,000 private addresses to hand out.
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "dns-monitor-vpc"
  }
}

# ─── SUBNET ───────────────────────────────────────────────────────────────────
# A slice of the network where our machine will live.
# 10.0.1.0/24 = 256 addresses, carved out of the /16 above.
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "dns-monitor-subnet"
  }
}

# ─── INTERNET ACCESS ──────────────────────────────────────────────────────────
# The doorway between our private network and the internet.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "dns-monitor-igw"
  }
}

# The signpost: "to reach anywhere on the internet (0.0.0.0/0), use the door."
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "dns-monitor-rt"
  }
}

# Attach the signpost to our room, so traffic there knows the way out.
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}