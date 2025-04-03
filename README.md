# TaoPulse

TaoPulse is an asynchronous API service for querying Tao dividends from the Bittensor blockchain with Redis caching and PostgreSQL storage.

https://www.loom.com/share/c11f57a3277b402dbfadbb3c935e2bf4  - running project and testing endpoints
https://www.loom.com/share/c1a82ef6b9c1437a92065dca3b53423f - load testing and implementation details

## Features

- FastAPI endpoint to query Tao dividends from the Bittensor blockchain
- Redis caching with configurable TTL for optimal performance
- PostgreSQL database for persistent storage of queries, sentiment analysis, and transactions
- Optional sentiment-based staking operations
- Dockerized setup for easy deployment and scaling

## Requirements

- Docker and Docker Compose
- Bittensor wallet (if performing staking operations)

## Quick Start with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/arhangel66/taopulse.git
   cd taopulse
   ```

2. Create a `.env` file based on the `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Update the environment variables in the `.env` file as needed.

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```
   This will start three services:
   - **taopulse**: The main application (FastAPI)
   - **redis**: The caching server
   - **postgres**: The database server

4. Check the status of your containers:
   ```bash
   docker-compose ps
   ```

5. View logs for troubleshooting:
   ```bash
   docker-compose logs -f taopulse
   ```

6. The API will be available at `http://localhost:8000`

7. API documentation is available at `http://localhost:8000/docs`

8. To stop the services:
   ```bash
   docker-compose down
   ```

9. To stop and remove all data (volumes):
   ```bash
   docker-compose down -v
   ```

## Bittensor Wallet Configuration

TaoPulse mounts your local Bittensor wallet directory to the Docker container. If you're using staking features, ensure your `.bittensor` directory is available at `~/.bittensor`.

If you need to create a new wallet:

1. Install Bittensor CLI locally:
   ```bash
   pip install bittensor
   ```

2. Create and register a wallet:
   ```bash
   btcli wallet new
   btcli wallet register
   ```

## Environment Variables

Important environment variables that can be set in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server hostname | redis |
| `REDIS_PORT` | Redis server port | 6379 |
| `CACHE_TTL` | Cache time-to-live in seconds | 120 |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://postgres:postgres@postgres:5432/taopulse |
| `DEFAULT_NETUID` | Default subnet ID | 18 |
| `DEFAULT_HOTKEY` | Default hotkey for operations | - |
| `WALLET_NAME` | Bittensor wallet name | main |
| `WALLET_HOTKEY` | Bittensor wallet hotkey | default |
| `MAX_STAKE_AMOUNT` | Maximum amount to stake/unstake | 100.0 |

## API Endpoints

### GET /api/v1/tao_dividends

Query Tao dividends from the Bittensor blockchain.

**Parameters:**
- `netuid` (optional): Subnet ID
- `hotkey` (optional): Account address
- `trade` (optional, default: false): Whether to trigger stake/unstake operations

**Response Example:**
```json
{
  "dividends": {
    "18": {
      "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa": 1000
    }
  },
  "cached": true,
  "collected_at": "2025-04-01T12:00:00Z",
  "trade": null
}
```

## Development and Customization

### Modifying the Docker Setup

You can modify the Docker Compose configuration in `docker-compose.yml`:

- Change port mappings
- Add additional services
- Modify volume configurations
- Adjust environment variables

### Scaling the Application

For high-load scenarios, you can scale the application:

```bash
docker-compose up -d --scale taopulse=3
```

Note: When scaling, you'll need to add a load balancer in front of the application.

## System Architecture

### Key Components

```mermaid
classDiagram
    class FastAPI {
        +app
        +router
    }
    
    class DividendService {
        +endpoint: str
        +substrate
        +is_warmed_up: bool
        +connect()
        +get_dividends(netuid, hotkey)
        +close()
    }
    
    class TradeService {
        +trade(netuid, hotkey, sentiment)
    }
    
    class RedisClient {
        +redis_pool
        +get_cache()
        +set_cache()
    }
    
    class Storage {
        +add_dividends()
        +add_twitter()
        +add_sentiment()
        +add_trade()
    }
    
    class ExecuteService {
        +trade()
    }
    
    class SentimentService {
        +analyze_tweets()
    }
    
    class TweetsService {
        +search_tweets()
    }
    
    FastAPI --> DividendService: uses
    FastAPI --> RedisClient: uses
    FastAPI --> ExecuteService: uses
    FastAPI --> Storage: uses
    
    ExecuteService --> TweetsService: calls
    ExecuteService --> SentimentService: calls
    ExecuteService --> TradeService: calls
```

### Sequence Diagram for /tao_dividend Endpoint

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Redis
    participant DividendService
    participant ExecuteService
    participant TweetsService
    participant SentimentService
    participant TradeService
    participant Storage
    participant Bittensor
    
    Client->>FastAPI: GET /tao_dividends?netuid=X&hotkey=Y&trade=true
    FastAPI->>Redis: Check cache
    
    alt Cache hit
        Redis-->>FastAPI: Return cached result
        FastAPI-->>Client: Return response with cached=true
    else Cache miss
        FastAPI->>DividendService: get_dividends(netuid, hotkey)
        DividendService->>Bittensor: Query TaoDividendsPerSubnet
        Bittensor-->>DividendService: Return dividend data
        DividendService-->>FastAPI: Return dividends
        
        FastAPI->>Storage: add_dividends(dividends, request_id, ...)
        
        opt trade=true
            FastAPI->>ExecuteService: trade(execute_input)
            ExecuteService->>TweetsService: search_tweets(netuid)
            TweetsService-->>ExecuteService: Return tweets
            ExecuteService->>Storage: Store tweets
            
            ExecuteService->>SentimentService: analyze_tweets(tweets)
            SentimentService-->>ExecuteService: Return sentiment score
            ExecuteService->>Storage: Store sentiment analysis
            
            ExecuteService->>TradeService: trade(netuid, hotkey, sentiment_score)
            
            alt sentiment > 0
                TradeService->>Bittensor: add_stake(amount)
            else sentiment < 0
                TradeService->>Bittensor: unstake(amount)
            end
            
            Bittensor-->>TradeService: Return transaction result
            TradeService-->>ExecuteService: Return trade result
            ExecuteService->>Storage: Store trade result
            ExecuteService-->>FastAPI: Return execute result
        end
        
        FastAPI->>Redis: Cache result for 2 minutes
        FastAPI-->>Client: Return response with cached=false
    end
```

## Redis Caching Configuration

The application uses Redis for caching blockchain query results. The cache TTL is set to 2 minutes by default.

Redis configuration can be modified through the following environment variables:

- `REDIS_HOST`: Redis server hostname (default: "redis" in Docker, "localhost" outside Docker)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_PASSWORD`: Redis password (default: empty)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 120)
- `REDIS_POOL_MAX_CONNECTIONS`: Maximum number of connections in the Redis connection pool (default: 10)

## Development Setup

To set up the development environment:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing

Run tests with:
```bash
pytest
