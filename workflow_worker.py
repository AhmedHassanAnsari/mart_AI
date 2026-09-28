from agent.reorder_workflow import create_workflow_runtime
from observability import flush_traces


def main() -> None:
    import time
    # Give the Dapr sidecar a few seconds to fully bind its gRPC server
    time.sleep(5)

    runtime = create_workflow_runtime()
    try:
        runtime.start()
        runtime.wait_for_worker_ready()
    finally:
        runtime.shutdown()
        flush_traces()


if __name__ == "__main__":
    main()