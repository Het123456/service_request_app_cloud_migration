# Load test results (Locust)

## What we tested

We used Locust to act like many people using the app at the same time. Each simulated user opens the request list, adds new requests and updates their status.

We tested two setups on AWS in Mumbai.

| Setup | App runs on | Database runs on |
|---|---|---|
| Stage 2 | EC2 t3.micro | MySQL in Docker on the same EC2 |
| Stage 3 | EC2 t3.micro | RDS MySQL db.t3.micro |

How we ran the tests:

1. Locust ran inside the EC2 instance, so home internet speed did not affect the numbers.
2. We tested 1, 10 and 50 users at the same time.
3. Each test ran for 60 seconds and was repeated 3 times. That gives 9 runs for each stage.
4. The database held exactly 1,000 rows before every run. Rows added by the test were removed after each run.

## Results

Response time is how long one request took, in milliseconds (ms). Lower is better. The median is a typical request. P95 means 95 out of 100 requests were this fast or faster. Each number is the average of the 3 runs.

| Users | Stage 2 median | Stage 3 median | Stage 2 P95 | Stage 3 P95 |
|---|---|---|---|---|
| 1 | 9.7 ms | 14.3 ms | 39.3 ms | 22.0 ms |
| 10 | 9.7 ms | 14.0 ms | 26.7 ms | 55.7 ms |
| 50 | 11.0 ms | 17.7 ms | 47.7 ms | 89.3 ms |

| | Stage 2 | Stage 3 |
|---|---|---|
| Total requests | 10,568 | 10,501 |
| Failed requests | 0 | 0 |
| Requests per second at 50 users | 48.5 | 48.1 |

## What the results show

1. Both setups handled every request. Not one request failed in all 18 runs.
2. Stage 2 was faster. A typical request took about 10 ms with the database on the same machine and about 14 to 18 ms with RDS.
3. The gap grows with more users. At 50 users the P95 time was 47.7 ms on Stage 2 and 89.3 ms on Stage 3.
4. Stage 3 had the better P95 at 1 user (22.0 ms against 39.3 ms).
5. Both setups had a few rare slow requests, up to about 640 ms on Stage 2 and 550 ms on Stage 3. They are too rare to change the median.
6. Requests per second was the same in both stages. Locust sends requests at a fixed pace, so this number depends on the number of users and not on the database.

## Why Stage 3 is slower

In Stage 2 the app and the database are on the same machine. With RDS every database query travels over the network to a separate server and back. One page needs several queries, so these small delays add up, and they add up more when many users are active.

Our project plan expected RDS might do better at 50 users, because the app and the database would no longer share one small machine. That did not happen. At this load, sharing one t3.micro does not seem to have slowed Stage 2 down.

## What this means

Stage 2 is faster and cheaper. Stage 3 adds a few milliseconds to each request, but AWS takes care of backups, updates and failover. The app stays quick in both setups, so the choice between them depends more on cost and maintenance effort than on speed. The file cost_effort.md compares those.

## Limits of this test

1. Each test ran for only 60 seconds.
2. 50 users is a small load. A busier system could behave differently.
3. We used the smallest instance sizes. Larger sizes would give different numbers.
4. All numbers come from one EC2 instance and one RDS instance, tested on one day.

Raw data: the CSV files in `results/locust/` on the `janak-work` branch.
