import asyncio
import os
import json
import psycopg
from psycopg import AsyncConnection
from dapr.clients import DaprClient
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("notification-bridge")

load_dotenv()

# Config
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Simulation mode for testing without Dapr sidecar
SIMULATION_MODE = os.getenv("DAPR_SIMULATION", "false").lower() == "true"

PUB_SUB_NAME = "inventory-pubsub"
TOPIC_NAME = "inventory-reorder"

async def run_bridge():
    # Handle Dapr client setup
    if SIMULATION_MODE:
        logger.info("!!! RUNNING IN SIMULATION MODE - Dapr publishing will be mocked !!!")
        dapr_client = None
    else:
        try:
            dapr_client = DaprClient()
            logger.info("Connected to Dapr Client.")
        except Exception as e:
            logger.error(f"Failed to connect to Dapr: {e}")
            return

    conn_str = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"

    while True:
        try:
            logger.info("Attempting to connect to Postgres...")
            async with await psycopg.AsyncConnection.connect(conn_str, autocommit=True) as conn:
                logger.info("Connected to Postgres. Listening for inventory reorder events...")

                async with conn.cursor() as cur:
                    await cur.execute("LISTEN inventory_reorder_events")

                # Process notifications
                async for notify in conn.notifies():
                    payload_str = notify.payload
                    logger.info(f"Received Postgres notification: {payload_str}")

                    try:
                        payload = json.loads(payload_str)

                        if SIMULATION_MODE:
                            logger.info(f"[SIMULATION] Would publish to {PUB_SUB_NAME}/{TOPIC_NAME}: {payload}")
                        else:
                            logger.info(f"Publishing event to Dapr topic {TOPIC_NAME}...")
                            dapr_client.publish_event(
                                pubsub_name=PUB_SUB_NAME,
                                topic_name=TOPIC_NAME,
                                data=json.dumps(payload).encode('utf-8')
                            )
                            logger.info("Event successfully published to Dapr.")

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON payload: {payload_str}")
                    except Exception as e:
                        logger.error(f"Error publishing to Dapr: {e}")

        except (psycopg.OperationalError, Exception) as e:
            logger.error(f"Connection lost or failed to connect: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        logger.info("Bridge shutting down...")
