# Cost and effort comparison

Running MySQL ourselves on the EC2 VM (Stage 2) versus using a managed
database, AWS RDS (Stage 3).

## Monthly cost

Source: AWS Pricing Calculator, Asia Pacific (Mumbai), on-demand prices,
730 hours a month, priced on 14 Nov 2026. Taxes and data transfer not included.

| Item | Option A: EC2 only (Stage 2) | Option B: EC2 + RDS (Stage 3) |
|---|---|---|
| EC2 t3.micro (0.0112 USD/hour) | 8.18 USD | 8.18 USD |
| EBS disk, 20 GB gp3 (0.0912 USD/GB) | 1.82 USD | 1.82 USD |
| RDS MySQL db.t3.micro, Single-AZ (0.025 USD/hour) | - | 18.25 USD |
| RDS storage, 20 GB gp3 | - | 2.62 USD |
| **Total per month** | **10.00 USD** | **30.87 USD** |
| Total per year | 120.00 USD | 370.44 USD |

Moving the database to RDS adds 20.87 USD a month, so Option B costs about
3.1 times as much as Option A.

Not included in the RDS price: RDS Proxy, Database Insights, Multi-AZ and
extra backup storage. With Multi-AZ the RDS instance cost roughly doubles.

## Setup effort

| Stage | Time | Notes |
|---|---|---|
| Stage 1: Local (Docker on laptop) | Not timed | Quick. One problem: macOS uses port 5000 for AirPlay, so the app moved to port 8000. |
| Stage 2: EC2 with MySQL in Docker | 40 min | EC2 and security group 15, Docker and environment 10, seeding and testing 15 |
| Stage 3: RDS | 28 min | RDS and security group 15, database and app configuration 8, testing 5 |

Stage 3 reused the EC2 instance from Stage 2, so its 28 minutes cover only the
database move. The app code did not change: only `DB_HOST` and the credentials.

## Who does the database work

| Task | MySQL on EC2 (Option A) | RDS (Option B) |
|---|---|---|
| Install and configure MySQL | Us (Docker image and compose file) | AWS |
| Backups | Us: nothing set up, would need a mysqldump job | AWS: automated daily backups and snapshots |
| Restore after data loss | Us, by hand from a dump | Restore from a snapshot in the console |
| Security patches and minor upgrades | Us | AWS, in a maintenance window |
| Monitoring | Us | CloudWatch metrics built in |
| Failover | None: if the VM fails, the database is down | Optional Multi-AZ standby (extra cost) |
| Scaling the database | Resize the whole VM, app included | Resize the database instance on its own |
| Resource sharing | App and database share 1 GB of memory | Database has its own instance |

## Summary

RDS costs about three times as much per month and adds roughly a millisecond
to each read, because every query crosses the network. In return the team no
longer installs, backs up, patches or monitors the database, and the database
can be resized or made highly available without touching the app.
