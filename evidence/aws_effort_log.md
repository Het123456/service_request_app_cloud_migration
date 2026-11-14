# AWS Deployment Effort Log (Ferin)

## Stage 2: Lift-and-Shift (EC2) - 11 Nov 2026
- AWS Account & Security Setup (Keypair, Budget Alert): 10 mins
- EC2 Instance Launch (t3.micro, Ubuntu 24.04, 20GB gp3): 5 mins
- Docker Installation & 1GB Swap Setup: 7 mins
- Repository Clone & .env Configuration: 3 mins
- Container Build & Database Seeding (1,000 rows): 5 mins
- Benchmark Executions (timing.py x3, page_timing.py x3): 10 mins
**Total Stage 2 Setup Effort: ~40 minutes**

## Stage 3: Refactor to Managed AWS RDS - 11 Nov 2026
- AWS RDS MySQL 8.4 Provisioning (db.t4g.micro, Single-AZ, 20GB gp3): 12 mins
- Security Group Inbound Rule Configuration (Allowing EC2 SG on 3306): 3 mins
- Schema Migration into RDS via Docker MySQL client: 2 mins
- App Configuration (docker-compose.rds.yml & .env.rds DB_HOST switch): 4 mins
- Database Seeding (1,000 records into RDS): 2 mins
- Benchmark Executions (timing.py x3, page_timing.py x3): 5 mins
**Total Stage 3 Setup Effort: ~28 minutes**
