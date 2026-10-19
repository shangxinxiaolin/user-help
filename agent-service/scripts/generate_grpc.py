"""Generate Python gRPC code from the Java-owned Protobuf contract."""

from pathlib import Path

from grpc_tools import protoc


SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROTO_ROOT = SERVICE_ROOT / "proto"
PROTO_FILE = PROTO_ROOT / "business_service.proto"
OUTPUT_ROOT = SERVICE_ROOT / "app" / "grpc_client" / "generated"


def generate() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "__init__.py").touch()

    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={OUTPUT_ROOT}",
            f"--grpc_python_out={OUTPUT_ROOT}",
            str(PROTO_FILE),
        ]
    )
    if result != 0:
        raise SystemExit(result)

    grpc_module = OUTPUT_ROOT / "business_service_pb2_grpc.py"
    content = grpc_module.read_text(encoding="utf-8")
    content = content.replace(
        "import business_service_pb2 as business__service__pb2",
        "from . import business_service_pb2 as business__service__pb2",
    )
    grpc_module.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    generate()
